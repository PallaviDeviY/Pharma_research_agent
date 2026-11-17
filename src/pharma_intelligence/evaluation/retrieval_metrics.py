from __future__ import annotations

import math
from typing import Iterable


def recall_at_k(ranked_ids: Iterable[str], relevant_ids: set[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    return len(set(list(ranked_ids)[:k]) & relevant_ids) / len(relevant_ids)


def precision_at_k(ranked_ids: Iterable[str], relevant_ids: set[str], k: int = 5) -> float:
    if k <= 0:
        return 0.0
    return len(set(list(ranked_ids)[:k]) & relevant_ids) / k


def reciprocal_rank(ranked_ids: Iterable[str], relevant_ids: set[str]) -> float:
    for index, value in enumerate(ranked_ids, start=1):
        if value in relevant_ids:
            return 1 / index
    return 0.0


def ndcg_at_k(ranked_ids: Iterable[str], relevant_ids: set[str], k: int = 5) -> float:
    if k <= 0 or not relevant_ids:
        return 0.0
    ids = list(ranked_ids)[:k]
    dcg = sum(1 / math.log2(rank + 1) for rank, value in enumerate(ids, start=1) if value in relevant_ids)
    ideal_count = min(k, len(relevant_ids))
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal if ideal else 0.0

