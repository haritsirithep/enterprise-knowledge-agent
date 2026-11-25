# Design Decisions

Why each piece is the way it is, and what I'd change for production.

## Data
- **10 docs: 6 policies (EN + TH), 1 confidential salary doc, 3 Thai chat logs.** The chats have slang (ป่ะ, มะ, ตัง), typos (เงิล, ลาพักร้อม), emoji, and one thread with **wrong** info (taxi "500 baht" vs the policy's 600). This tests whether the agent trusts the official policy over gossip.
- **Policies are real PDFs, chats are `.txt` exports.** That matches the brief ("data scattered in PDFs and chats"). Both are generated from `data/source_md/` by `scripts/build_docs.py`, so the content stays editable.
- **Metadata lives in `catalog.yaml`** (`doc_id`, `doc_type`, `access_level`), because a PDF can't carry it. It drives citations, source priority and RBAC. This is a small version of a document registry.
- **Thai PDF extraction is messy, so I tested it instead of trusting it.** I rendered the PDFs and compared the extracted text against the source:
  - `pypdf` adds spaces around Thai vowel/tone marks ("ต ้อง") and a random junk character after สระอำ ("กำ=หนด", "ทำ_งาน"). The junk character differs per file.
  - `pypdfium2` was worse: it reorders the marks.
  - Turning off text shaping when making the PDF gives clean extraction, but the PDF *looks* broken (missing vowels). That's not acceptable.
  - Fix: keep `pypdf` and add `clean_text()` rules. Result: **100% character match** on all 7 PDFs (ignoring whitespace). The trade-off: it can also join a real phrase space in Thai, which is harmless for search since Thai has no spaces between words.
  - This is exactly the "AI must read messy files" problem from the exec feedback: messy input needs a cleaning layer, plus a measurement that proves it works.
- **Size-based chunking (~600 chars, 1-line overlap)**, not heading-based. Headings disappear in PDF text, and uploaded files can have any shape. Paragraph breaks still close a chunk, so chat threads don't mix. The title is prepended to every chunk. Retrieval stayed at 15/15 after the switch.

## Upload
- **Indexed immediately**: only the new chunks are embedded; BM25 is rebuilt (milliseconds at this size).
- **Same RBAC rule as retrieval**: an employee can't add an executive-only doc, and the Documents tab only lists what your role can see.
- **Same file twice** gets the same content-hash ID, so it isn't indexed twice.
- **Risk**: an uploaded doc is a path for *indirect prompt injection*. The answer prompt already treats sources as data, not instructions. In production, uploads would also need an owner/approval step.

## Retrieval
- **Hybrid BM25 + dense, merged with Reciprocal Rank Fusion (RRF).**
  - Dense (multilingual-e5-small) handles meaning and cross-language matches (EN question → TH doc).
  - BM25 with `pythainlp` word splitting handles exact terms: `ExpenseHub`, `1234`, `L3`.
  - RRF merges by rank, so we don't have to calibrate two different score scales.
- **multilingual-e5-small**: free, local, supports Thai, small (~470 MB). Trade-off: its similarity scores are bunched together (off-topic ≈ 0.74, on-topic ≈ 0.82+), so the threshold is sensitive. Upgrade path: bge-m3, or an API embedding model.
- **numpy instead of a vector DB.** The 23 chunks fit in memory and search in microseconds. A DB would add setup without adding anything to show. Production: pgvector (see architecture doc).
- **RBAC is a pre-filter.** Chunks the role can't access are removed *before* ranking, so the LLM never sees them and can't leak them. Filtering after generation would be too late.

## Guardrails (defense in depth)
1. **Regex rules (EN + TH)**: free, instant, catch the obvious attacks before any LLM call.
2. **LLM triage**: catches paraphrased attacks ("pretend you are the HR director...") and off-topic questions. The same call also rewrites slang into clean text for search, so we get two jobs for one call.
3. **Indirect injection**: the answer prompt says the sources are *data, not instructions*. A poisoned chat message can't take over the agent.
4. **Output validation**: every answer must cite `[S#]`, and only sources we actually gave the model. A made-up citation means fallback.

## Confidence and fallback
- **Gate 1 (retrieval score ≥ 0.80)**: a cheap pre-filter. Below it we skip the LLM call entirely.
  - With the first (markdown, section-based) chunks it separated cleanly: lowest answerable 0.819 vs "not in KB" 0.777–0.791.
  - After switching to PDF + size-based chunks, the ranges **overlap** (lowest answerable 0.827, highest "not in KB" 0.832), so Gate 2 now catches those cases.
  - I kept 0.80 on purpose: a gate that's too strict blocks real answers (bad for users); one that's too loose only costs an extra LLM call (Gate 2 still catches it). In production I'd tune this on real logged queries, or replace raw cosine with a reranker score that separates better.
  - Lesson: **a threshold is tied to the embedding model + chunking. Change either, re-run the eval.** That's how we caught this.
- **Gate 2 (LLM `answerable` + confidence ≥ 0.6 + valid citations)**: catches cases where retrieval finds *related* text but not an answer. Example: WFH, which is only speculation in a chat.
- **Unofficial sources can't stand alone (enforced in code).** Testing showed the WFH question was *sometimes* answered from the sales chat alone (about 1 in 4 runs), even though the prompt says chats may be wrong. So the catalog marks that chat `official: false`, the LLM sees it labelled `UNOFFICIAL`, and Gate 2 rejects any answer whose citations are all unofficial (`only_unofficial_sources`). After the change: 6/6 fallbacks. Lesson: when a rule matters, put it in code, not only in the prompt.
- **When a chat conflicts with a policy, the answer uses the policy only.** It doesn't repeat or cite the conflicting chat (e.g. the "500 THB" taxi rumour), so users never see the wrong number at all. Answers also don't mention the company name.
- **Every fallback is logged** to `logs/unanswered.jsonl` with a trace ID. This is the to-do list for growing the knowledge base.
- **Caveat**: LLM self-confidence isn't calibrated. In production I'd calibrate thresholds against a labelled eval set and add an LLM-as-judge faithfulness check on a sample.

## LLM
- **LiteLLM** gives one interface for Gemini, OpenAI, Anthropic, Ollama and more. The user picks the model in `.env` or in the UI dropdown, and avoids vendor lock-in.
- **Default: Gemini free tier.** No cost and good Thai. Trade-off: free-tier rate limits are low and can change, so the code retries (`num_retries=2`) and the eval has a `--delay`.
- **JSON output** for both calls, so the pipeline reads structured fields instead of parsing free text.

## UI
- **Gradio Blocks** (not `ChatInterface`): it shows sources, the RBAC role switch, the model switch, a details panel (scores, trace ID, latency) and the fallback log tab, all in one demo.

## Observability (prototype level)
- Every request gets a `trace_id` and one JSONL line: query, role, status, reason, scores, sources, model, latency. This maps directly to CloudWatch Logs / Logs Insights in production.
- **`served_model`**: the exact model version that answered. Two reasons: (1) with a fallback chain, the requested model isn't always the one that answered; (2) `-latest` aliases silently move to new versions (we saw `gemini-flash-lite-latest` → `gemini-3.5-flash-lite`). If quality changes overnight, this field tells you whether the model changed. In production, pin exact versions.
- **`rejected_answer`**: when gate 2 blocks an answer, the raw LLM output is logged. This came from a real debugging session: one answer was rejected for `invalid_citations`, I couldn't reproduce it in 5 retries, and without the raw text there was no way to find the root cause. Log what you need for RCA *before* the incident.
- **Fallback chain + timeout**: during testing, Gemini's free tier returned 503 "high demand" for `gemini-flash-latest`. Fallbacks keep the app answering. Trade-off: worst-case latency = timeout × attempts (we saw ~90s), so production needs a total time budget, not only a per-call timeout.
