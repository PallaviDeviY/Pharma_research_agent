from __future__ import annotations

from collections import defaultdict
from typing import Any

from pharma_intelligence.config import settings
from pharma_intelligence.retrieval.bm25 import BM25Retriever
from pharma_intelligence.retrieval.reranker import rerank
from pharma_intelligence.retrieval.vector_search import SentenceTransformerRetriever, TfidfVectorRetriever


class HybridRetriever:
    def __init__(self, chunks: list[dict[str, Any]]):
        self.chunks = chunks
        self.bm25 = BM25Retriever(chunks)
        if settings.vector_mode == "sentence-transformer":
            self.vector = SentenceTransformerRetriever(chunks, settings.embedding_model)
        else:
            self.vector = TfidfVectorRetriever(chunks)

    def search(self, query: str, k: int = 5, candidate_k: int = 30) -> list[dict[str, Any]]:
        if not self.chunks or k <= 0:
            return []
        lexical = self.bm25.search(query, candidate_k)
        vectors = self.vector.search(query, candidate_k)
        by_chunk: dict[int, dict[str, Any]] = {}
        ranks: dict[int, list[int]] = defaultdict(list)
        for rank, hit in enumerate(lexical, start=1):
            key = hit["chunk_id"]
            by_chunk[key] = hit
            ranks[key].append(rank)
        for rank, hit in enumerate(vectors, start=1):
            key = hit["chunk_id"]
            by_chunk.setdefault(key, hit)
            ranks[key].append(rank)
        fused = []
        for key, hit in by_chunk.items():
            score = sum(1 / (60 + rank) for rank in ranks[key])
            fused.append(dict(hit, rrf_score=score, retrieval_method="hybrid"))
        fused.sort(key=lambda hit: hit["rrf_score"], reverse=True)
        reranked = rerank(query, fused[:candidate_k], max(k * 3, k))
        # Return one best chunk per source record to avoid flooding the report with duplicate citations.
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for hit in reranked:
            if hit["document_id"] in seen:
                continue
            seen.add(hit["document_id"])
            unique.append(hit)
            if len(unique) >= k:
                break
        return unique

