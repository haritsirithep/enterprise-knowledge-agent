"""Hybrid retrieval: BM25 (keywords) + dense embeddings, merged with Reciprocal Rank Fusion.

RBAC is applied *before* ranking: chunks the role cannot see are never scored or returned.
"""
from dataclasses import dataclass
import string

import numpy as np
from pythainlp.tokenize import word_tokenize
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .config import ROLE_ACCESS
from .ingest import Chunk

RRF_K = 60  # standard constant for Reciprocal Rank Fusion


@dataclass
class Hit:
    chunk: Chunk
    dense_score: float
    bm25_score: float
    rrf_score: float


def tokenize(text: str) -> list[str]:
    tokens = word_tokenize(text.lower(), engine="newmm", keep_whitespace=False)
    return [t for t in tokens if t.strip() and t not in string.punctuation]


class HybridRetriever:
    def __init__(self, chunks: list[Chunk], embedding_model: str):
        self.model = SentenceTransformer(embedding_model)
        self.chunks: list[Chunk] = []
        self.doc_vectors = np.empty((0, self.model.get_embedding_dimension()), dtype=np.float32)
        self.add_chunks(chunks)

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Add new chunks to the live index (used for uploads). Only the new chunks are embedded."""
        if not chunks:
            return
        # e5 models expect "passage: " / "query: " prefixes.
        vectors = self.model.encode([f"passage: {c.text}" for c in chunks], normalize_embeddings=True)
        self.chunks += chunks
        self.doc_vectors = np.vstack([self.doc_vectors, vectors])
        # BM25 needs corpus-wide stats, so rebuild it. Cheap at this size (milliseconds).
        self.bm25 = BM25Okapi([tokenize(c.text) for c in self.chunks])

    def search(self, query: str, role: str, top_k: int = 4, keyword_query: str | None = None) -> list[Hit]:
        allowed = np.array([c.access_level in ROLE_ACCESS[role] for c in self.chunks])

        query_vector = self.model.encode(f"query: {query}", normalize_embeddings=True)
        dense = self.doc_vectors @ query_vector
        bm25 = self.bm25.get_scores(tokenize(keyword_query or query))

        allowed_ids = np.flatnonzero(allowed)
        dense_rank = allowed_ids[np.argsort(-dense[allowed_ids])]
        bm25_rank = allowed_ids[np.argsort(-bm25[allowed_ids])]

        rrf = {}
        for ranking in (dense_rank, bm25_rank):
            for rank, idx in enumerate(ranking):
                rrf[idx] = rrf.get(idx, 0.0) + 1 / (RRF_K + rank + 1)

        best = sorted(rrf, key=rrf.get, reverse=True)[:top_k]
        return [
            Hit(self.chunks[i], float(dense[i]), float(bm25[i]), rrf[i])
            for i in best
        ]
