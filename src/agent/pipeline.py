"""End-to-end flow for one question.

  query
    -> [1] rule guardrail (regex, no LLM)            -> refuse
    -> [2] LLM triage: scope check + query rewrite   -> refuse, or short reply for greetings
    -> [3] hybrid retrieval with RBAC filter
    -> [4] gate 1: retrieval score < threshold       -> fallback + log
    -> [5] LLM answer with [S#] citations
    -> [6] gate 2: not answerable / low confidence / bad citations -> fallback + log
    -> answer + sources
"""
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from . import guardrails
from .config import ROLE_ACCESS, settings
from .ingest import Document, chunk_document, load_documents, save_upload
from .llm import complete_json
from .logger import log_event
from .prompts import ANSWER_SYSTEM, ANSWER_USER, TRIAGE_SYSTEM
from .retriever import Hit, HybridRetriever


@dataclass
class Source:
    label: str  # S1, S2 ...
    doc_id: str
    title: str
    section: str
    doc_type: str
    score: float


@dataclass
class Result:
    status: str  # "answered" | "greeting" | "refused" | "fallback" | "error"
    answer: str
    reason: str = ""
    sources: list[Source] = field(default_factory=list)
    confidence: float | None = None
    retrieval_score: float | None = None
    rewritten_query: str = ""
    trace_id: str = ""
    latency_ms: int = 0
    model: str = ""  # model the user asked for
    served_model: str = ""  # exact model version that answered ("-latest" aliases resolve here; also shows fallbacks)
    rejected_answer: str = ""  # LLM answer blocked by gate 2, kept for debugging


def format_sources(hits: list[Hit]) -> str:
    return "\n\n".join(
        f"[S{i}] (type: {h.chunk.doc_type}, doc: {h.chunk.doc_id})\n{h.chunk.text}"
        for i, h in enumerate(hits, start=1)
    )


class KnowledgeAgent:
    def __init__(self):
        self.documents = load_documents(settings.docs_dir) + load_documents(settings.uploads_dir)
        chunks = [c for doc in self.documents for c in chunk_document(doc)]
        self.retriever = HybridRetriever(chunks, settings.embedding_model)

    def list_documents(self, role: str) -> list[Document]:
        """Documents this role may see. Same RBAC rule as retrieval."""
        return [d for d in self.documents if d.access_level in ROLE_ACCESS[role]]

    def add_document(self, path: Path, title: str, doc_type: str, access_level: str, role: str) -> Document:
        """Save an uploaded file and add it to the live index, so it's searchable immediately."""
        if access_level not in ROLE_ACCESS[role]:
            raise PermissionError(f"Role '{role}' cannot add '{access_level}' documents.")
        doc = save_upload(path, settings.uploads_dir, title, doc_type, access_level)
        if any(d.doc_id == doc.doc_id for d in self.documents):
            return doc  # same file uploaded again: already indexed
        self.documents.append(doc)
        self.retriever.add_chunks(chunk_document(doc))
        return doc

    def ask(self, query: str, role: str = "employee", model: str | None = None, api_key: str | None = None) -> Result:
        model = model or settings.llm_model
        api_key = (api_key or "").strip() or None
        start = time.perf_counter()
        trace_id = uuid.uuid4().hex[:12]
        try:
            result = self._run(query, role, model, api_key)
        except Exception as e:  # missing API key, rate limit, provider outage, bad JSON ...
            reason = str(e)[:300]
            if api_key:  # some provider errors echo the request URL, which can contain the key
                reason = reason.replace(api_key, "***")
            result = Result("error", f"System error ({type(e).__name__}). Please try again or contact support.",
                            reason=reason)
        result.trace_id = trace_id
        result.model = model
        result.latency_ms = int((time.perf_counter() - start) * 1000)
        self._log(query, role, result)
        return result

    def _run(self, query: str, role: str, model: str, api_key: str | None) -> Result:
        lang = guardrails.detect_lang(query)

        # [1] Fast rule-based guardrail. Catches obvious attacks with zero LLM cost.
        rule = guardrails.check_input_rules(query)
        if rule.blocked:
            return Result("refused", guardrails.REFUSAL_INJECTION[lang], reason=rule.reason)

        # [2] LLM triage: catches paraphrased attacks + off-topic, and fixes slang/typos for search.
        triage, served_model = complete_json(query, model, system=TRIAGE_SYSTEM, api_key=api_key)
        category = triage.get("category", "out_of_scope")
        rewritten = triage.get("rewritten_query") or query
        if category == "injection":
            return Result("refused", guardrails.REFUSAL_INJECTION[lang], reason="injection_llm",
                          rewritten_query=rewritten, served_model=served_model)
        if category == "greeting":
            return Result("greeting", triage.get("reply") or guardrails.GREETING[lang], reason="greeting",
                          served_model=served_model)
        if category != "in_scope":
            return Result("refused", guardrails.REFUSAL_OUT_OF_SCOPE[lang], reason="out_of_scope",
                          rewritten_query=rewritten, served_model=served_model)

        # [3] Retrieve. Dense search uses the clean rewrite; keyword search also sees the original wording.
        hits = self.retriever.search(rewritten, role, settings.top_k, keyword_query=f"{query} {rewritten}")
        retrieval_score = max((h.dense_score for h in hits), default=0.0)
        sources = [
            Source(f"S{i}", h.chunk.doc_id, h.chunk.title, h.chunk.section, h.chunk.doc_type, round(h.dense_score, 3))
            for i, h in enumerate(hits, start=1)
        ]

        def fallback(reason: str, confidence: float | None = None, rejected_answer: str = "") -> Result:
            return Result("fallback", guardrails.FALLBACK[lang], reason=reason, sources=sources,
                          confidence=confidence, retrieval_score=retrieval_score, rewritten_query=rewritten,
                          served_model=served_model, rejected_answer=rejected_answer)

        # [4] Gate 1: nothing similar enough in the knowledge base. Skip the LLM call entirely.
        if retrieval_score < settings.retrieval_threshold:
            return fallback("low_retrieval_score")

        # [5] Generate a grounded answer.
        output, served_model = complete_json(
            ANSWER_USER.format(sources=format_sources(hits), question=query),
            model,
            system=ANSWER_SYSTEM.format(lang="Thai" if lang == "th" else "English"),
            api_key=api_key,
        )
        answer = output.get("answer", "")
        confidence = float(output.get("confidence", 0.0))
        cited = guardrails.extract_citations(answer)

        # [6] Gate 2: validate the output before showing it.
        if not output.get("answerable", False):
            return fallback("llm_not_answerable", confidence, answer)
        if confidence < settings.answer_threshold:
            return fallback("low_answer_confidence", confidence, answer)
        if not guardrails.citations_are_valid(cited, {s.label for s in sources}):
            return fallback("invalid_citations", confidence, answer)

        return Result("answered", answer, sources=[s for s in sources if s.label in cited],
                      confidence=confidence, retrieval_score=retrieval_score, rewritten_query=rewritten,
                      served_model=served_model)

    def _log(self, query: str, role: str, result: Result) -> None:
        record = {
            "trace_id": result.trace_id,
            "query": query,
            "role": role,
            "status": result.status,
            "reason": result.reason,
            "rewritten_query": result.rewritten_query,
            "retrieval_score": result.retrieval_score,
            "confidence": result.confidence,
            "sources": [s.doc_id for s in result.sources],
            "model": result.model,
            "served_model": result.served_model,
            "latency_ms": result.latency_ms,
        }
        if result.rejected_answer:
            record["rejected_answer"] = result.rejected_answer
        log_event(settings.logs_dir / "queries.jsonl", record)
        if result.status == "fallback":
            log_event(settings.logs_dir / "unanswered.jsonl", record)
