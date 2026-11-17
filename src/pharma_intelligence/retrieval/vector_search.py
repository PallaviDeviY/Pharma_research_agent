from __future__ import annotations

import math
from collections import Counter
from functools import lru_cache
from typing import Any

from pharma_intelligence.retrieval.tokenize import tokenize


class TfidfVectorRetriever:
    """Deterministic local sparse-vector baseline (word TF-IDF, cosine similarity)."""

    def __init__(self, chunks: list[dict[str, Any]]):
        self.chunks = chunks
        self.tokens = [tokenize(chunk["text"]) for chunk in chunks]
        self.term_frequency = [Counter(tokens) for tokens in self.tokens]
        frequencies: Counter[str] = Counter()
        for terms in self.term_frequency:
            frequencies.update(terms.keys())
        count = max(1, len(chunks))
        self.idf = {term: math.log((1 + count) / (1 + frequency)) + 1 for term, frequency in frequencies.items()}
        self.vectors: list[dict[str, float]] = []
        self.norms: list[float] = []
        for tf in self.term_frequency:
            weights = {term: (1 + math.log(freq)) * self.idf[term] for term, freq in tf.items()}
            self.vectors.append(weights)
            self.norms.append(math.sqrt(sum(value * value for value in weights.values())))

    def search(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        tf = Counter(tokenize(query))
        if not tf:
            return []
        query_vector = {term: (1 + math.log(freq)) * self.idf[term] for term, freq in tf.items() if term in self.idf}
        query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
        if query_norm == 0:
            return []
        ranked = []
        for index, chunk in enumerate(self.chunks):
            vector = self.vectors[index]
            dot = sum(value * vector.get(term, 0.0) for term, value in query_vector.items())
            score = dot / (query_norm * self.norms[index]) if self.norms[index] else 0.0
            if score > 0:
                ranked.append((score, chunk))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [dict(chunk, score=score, retrieval_method="tfidf-vector") for score, chunk in ranked[:max(0, k)]]


@lru_cache(maxsize=2)
def _load_sentence_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Install the optional semantic dependencies with `pip install -e '.[semantic]'`.") from exc
    return SentenceTransformer(model_name)


class SentenceTransformerRetriever:
    """Optional dense semantic vector retriever; downloads its model on first use."""

    def __init__(self, chunks: list[dict[str, Any]], model_name: str):
        self.chunks = chunks
        self.model = _load_sentence_model(model_name)
        self.embeddings = self.model.encode(
            [chunk["text"] for chunk in chunks], normalize_embeddings=True, convert_to_numpy=True
        ) if chunks else None

    def search(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        if not self.chunks or k <= 0:
            return []
        query_embedding = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = self.embeddings @ query_embedding
        ranked = sorted(enumerate(scores.tolist()), key=lambda pair: pair[1], reverse=True)
        return [dict(self.chunks[index], score=float(score), retrieval_method="sentence-transformer-vector")
                for index, score in ranked[:k] if score > 0]

