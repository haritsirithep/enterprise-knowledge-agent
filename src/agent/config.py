"""All tunable settings in one place. Override any of them in .env."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    llm_model: str = os.getenv("LLM_MODEL", "gemini/gemini-flash-lite-latest")
    # Tried in order if the main model fails (e.g. 503 "high demand" on the free tier).
    fallback_models: tuple[str, ...] = tuple(
        m.strip() for m in os.getenv("FALLBACK_MODELS", "gemini/gemini-flash-latest,gemini/gemini-3.5-flash").split(",")
        if m.strip()
    )
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "30"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    top_k: int = int(os.getenv("TOP_K", "4"))
    # Gate 1: best dense similarity must reach this, or we fall back without calling the LLM.
    retrieval_threshold: float = float(os.getenv("RETRIEVAL_THRESHOLD", "0.80"))
    # Gate 2: the LLM's own confidence that the answer is supported by the sources.
    answer_threshold: float = float(os.getenv("ANSWER_THRESHOLD", "0.6"))
    docs_dir: Path = ROOT / "data" / "docs"  # base knowledge base (committed)
    uploads_dir: Path = ROOT / "data" / "uploads"  # files users add from the UI (not committed)
    logs_dir: Path = ROOT / "logs"


settings = Settings()

# Which document access levels each role can see (RBAC at the retrieval layer).
ROLE_ACCESS = {
    "employee": {"all"},
    "executive": {"all", "executive"},
}
