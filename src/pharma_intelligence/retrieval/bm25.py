from __future__ import annotations

import math
from collections import Counter
from typing import Any

from pharma_intelligence.retrieval.tokenize import tokenize


class BM25Retriever:
    def __init__(self, chunks: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(chunk["text"]) for chunk in chunks]
        self.lengths = [len(tokens) for tokens in self.tokens]
        self.average_length = sum(self.lengths) / max(1, len(self.lengths))
        self.term_frequency = [Counter(tokens) for tokens in self.tokens]
        document_frequency: Counter[str] = Counter()
        for tokens in self.tokens:
            document_frequency.update(set(tokens))
        n = max(1, len(chunks))
        self.idf = {term: math.log(1 + (n - frequency + 0.5) / (frequency + 0.5)) for term, frequency in document_frequency.items()}

    def search(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        terms = set(tokenize(query))
        if not terms:
            return []
        ranked = []
        for index, chunk in enumerate(self.chunks):
            length = self.lengths[index]
            score = 0.0
            for term in terms:
                frequency = self.term_frequency[index].get(term, 0)
                if frequency:
                    denom = frequency + self.k1 * (1 - self.b + self.b * length / max(1, self.average_length))
                    score += self.idf.get(term, 0.0) * frequency * (self.k1 + 1) / denom
            if score > 0:
                ranked.append((score, chunk))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [dict(chunk, score=score, retrieval_method="bm25") for score, chunk in ranked[:max(0, k)]]

