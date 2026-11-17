from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharma_intelligence.config import settings
from pharma_intelligence.database.queries import ResearchDatabase
from pharma_intelligence.evaluation.retrieval_metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from pharma_intelligence.retrieval.bm25 import BM25Retriever
from pharma_intelligence.retrieval.hybrid_search import HybridRetriever
from pharma_intelligence.retrieval.vector_search import TfidfVectorRetriever


def _unique_document_ids(hits: list[dict[str, Any]]) -> list[str]:
    output: list[str] = []
    for hit in hits:
        doc_id = f"{hit['source']}:{hit['external_id']}"
        if doc_id not in output:
            output.append(doc_id)
    return output


def evaluate(database: ResearchDatabase, dataset_path: Path | None = None) -> dict[str, Any]:
    path = dataset_path or Path(__file__).resolve().parents[3] / "data" / "processed" / "gold_queries.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks = database.get_chunks()
    retrievers = {
        "BM25": BM25Retriever(chunks),
        "TF-IDF vector": TfidfVectorRetriever(chunks),
        "Hybrid + reranker": HybridRetriever(chunks),
    }
    totals = {name: {"recall@5": 0.0, "precision@5": 0.0, "mrr": 0.0, "ndcg@5": 0.0} for name in retrievers}
    for row in rows:
        relevant = set(row["relevant_document_ids"])
        for name, retriever in retrievers.items():
            hits = retriever.search(row["query"], k=5)
            ranked = _unique_document_ids(hits)
            totals[name]["recall@5"] += recall_at_k(ranked, relevant, 5)
            totals[name]["precision@5"] += precision_at_k(ranked, relevant, 5)
            totals[name]["mrr"] += reciprocal_rank(ranked, relevant)
            totals[name]["ndcg@5"] += ndcg_at_k(ranked, relevant, 5)
    count = max(1, len(rows))
    return {"query_count": len(rows), "document_count": len(database.search_documents()),
            "retrievers": {name: {metric: round(value / count, 4) for metric, value in metrics.items()}
                           for name, metrics in totals.items()}}


def main() -> None:
    database = ResearchDatabase(settings.database_path)
    try:
        print(json.dumps(evaluate(database), indent=2))
    finally:
        database.close()


if __name__ == "__main__":
    main()

