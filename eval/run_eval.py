"""Evaluate the agent on eval/questions.jsonl.

  python eval/run_eval.py                    # full run (calls the LLM)
  python eval/run_eval.py --retrieval-only   # no LLM, no API key needed
  python eval/run_eval.py --delay 5          # wait between questions (free-tier rate limits)

Metrics:
  - status accuracy: did we answer / fall back / refuse when we should?
  - retrieval hit@k: for answerable questions, is an expected doc in the top-k?
  - source accuracy: for answered questions, does the cited source include an expected doc?
"""
import argparse
import json
import statistics
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent.config import settings  # noqa: E402
from agent.pipeline import KnowledgeAgent  # noqa: E402


def load_questions() -> list[dict]:
    lines = (ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


def eval_retrieval(agent: KnowledgeAgent, questions: list[dict]) -> None:
    answerable = [q for q in questions if q["expected_docs"]]
    hits = 0
    for q in answerable:
        results = agent.retriever.search(q["question"], q["role"], settings.top_k)
        found = any(h.chunk.doc_id in q["expected_docs"] for h in results)
        hits += found
        print(f"{q['id']:4} {'HIT ' if found else 'MISS'} {q['question']}")
    print(f"\nRetrieval hit@{settings.top_k}: {hits}/{len(answerable)} = {hits / len(answerable):.0%}")


def eval_full(agent: KnowledgeAgent, questions: list[dict], model: str, delay: float) -> None:
    rows = []
    for q in questions:
        result = agent.ask(q["question"], role=q["role"], model=model)
        cited = {s.doc_id for s in result.sources}
        source_ok = None
        if q["expect"] == "answered" and result.status == "answered":
            source_ok = bool(cited & set(q["expected_docs"]))
        rows.append({
            "id": q["id"], "question": q["question"], "role": q["role"],
            "expect": q["expect"], "got": result.status, "reason": result.reason,
            "pass": result.status == q["expect"], "source_ok": source_ok,
            "confidence": result.confidence, "retrieval_score": result.retrieval_score,
            "latency_ms": result.latency_ms, "answer": result.answer,
        })
        mark = "PASS" if rows[-1]["pass"] else "FAIL"
        print(f"{q['id']:4} {mark} expect={q['expect']:8} got={result.status:8} ({result.reason or '-'}) {result.latency_ms}ms")
        time.sleep(delay)

    total = Counter(r["expect"] for r in rows)
    passed = Counter(r["expect"] for r in rows if r["pass"])
    print("\nStatus accuracy by category:")
    for category in ("answered", "greeting", "fallback", "refused"):
        print(f"  {category:9} {passed[category]}/{total[category]}")
    print(f"  overall   {sum(passed.values())}/{len(rows)} = {sum(passed.values()) / len(rows):.0%}")

    sourced = [r for r in rows if r["source_ok"] is not None]
    if sourced:
        ok = sum(r["source_ok"] for r in sourced)
        print(f"Source accuracy (answered): {ok}/{len(sourced)}")

    latencies = [r["latency_ms"] for r in rows]
    print(f"Latency median={statistics.median(latencies):.0f}ms  max={max(latencies)}ms")

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out_path.write_text(json.dumps({"model": model, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--model", default=settings.llm_model)
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between questions")
    args = parser.parse_args()

    agent = KnowledgeAgent()
    questions = load_questions()
    if args.retrieval_only:
        eval_retrieval(agent, questions)
    else:
        eval_full(agent, questions, args.model, args.delay)
