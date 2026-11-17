from __future__ import annotations

from collections import defaultdict
from typing import Any

from pharma_intelligence.database.queries import ResearchDatabase
from pharma_intelligence.retrieval.hybrid_search import HybridRetriever


class EvidenceAgent:
    SOURCES = ("clinicaltrials.gov", "openfda.label", "pubmed")

    def __init__(self, database: ResearchDatabase):
        self.database = database

    def retrieve(self, question: str, drug_names: list[str], per_source: int = 3) -> list[dict[str, Any]]:
        chunks = self.database.get_chunks(drug_names)
        selected: dict[str, dict[str, Any]] = {}
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for chunk in chunks:
            grouped[chunk["source"]].append(chunk)
        for source in self.SOURCES:
            source_chunks = grouped.get(source, [])
            if not source_chunks:
                continue
            for hit in HybridRetriever(source_chunks).search(question, k=per_source, candidate_k=30):
                selected[hit["document_id"]] = hit
        return sorted(selected.values(), key=lambda hit: hit.get("rerank_score", 0), reverse=True)

