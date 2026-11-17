from __future__ import annotations

from typing import Any

from pharma_intelligence.retrieval.tokenize import tokenize


def rerank(query: str, candidates: list[dict[str, Any]], k: int = 10) -> list[dict[str, Any]]:
    """Small transparent lexical reranker; preserves source IDs for citation checks."""
    query_terms = set(tokenize(query))
    rescored = []
    for hit in candidates:
        text_terms = set(tokenize(f"{hit.get('title', '')} {hit.get('text', '')}"))
        coverage = len(query_terms & text_terms) / max(1, len(query_terms))
        title_coverage = len(query_terms & set(tokenize(hit.get("title", "")))) / max(1, len(query_terms))
        score = float(hit.get("rrf_score", hit.get("score", 0))) + coverage + title_coverage * 0.5
        rescored.append((score, hit))
    rescored.sort(key=lambda pair: pair[0], reverse=True)
    return [dict(hit, rerank_score=score) for score, hit in rescored[:max(0, k)]]

