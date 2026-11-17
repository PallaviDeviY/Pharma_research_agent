import json
from pathlib import Path

import pytest

from pharma_intelligence.agents.conflict_screen import screen_conflicts
from pharma_intelligence.evaluation.retrieval_metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from pharma_intelligence.ingestion.clinical_trials import parse_study
from pharma_intelligence.ingestion.common import SourceError
from pharma_intelligence.ingestion import pipeline
from pharma_intelligence.ingestion.pubmed import fetch_publications
from pharma_intelligence.models import EvidenceDocument
from pharma_intelligence.retrieval.bm25 import BM25Retriever
from pharma_intelligence.retrieval.hybrid_search import HybridRetriever
from pharma_intelligence.retrieval.vector_search import TfidfVectorRetriever
from pharma_intelligence.safety.citation_validator import citation_coverage


def chunk(identifier, text, source="pubmed"):
    return {"chunk_id": identifier, "document_id": f"{source}:{identifier}", "source": source,
            "external_id": str(identifier), "drug_name": "semaglutide", "title": text[:40],
            "text": text, "url": f"https://pubmed.ncbi.nlm.nih.gov/{identifier}/", "published_at": None,
            "metadata_json": "{}"}


def test_bm25_and_vector_rank_relevant_document_first():
    corpus = [chunk(1, "semaglutide cardiovascular outcomes in type 2 diabetes"),
              chunk(2, "aspirin headache pain study")]
    assert BM25Retriever(corpus).search("semaglutide cardiovascular outcomes")[0]["chunk_id"] == 1
    assert TfidfVectorRetriever(corpus).search("semaglutide cardiovascular outcomes")[0]["chunk_id"] == 1
    assert HybridRetriever(corpus).search("semaglutide cardiovascular outcomes")[0]["chunk_id"] == 1


def test_empty_retrieval_returns_no_results():
    assert BM25Retriever([]).search("semaglutide") == []
    assert TfidfVectorRetriever([]).search("semaglutide") == []
    assert HybridRetriever([]).search("semaglutide") == []
    assert BM25Retriever([chunk(1, "unrelated text")]).search("semaglutide") == []


def test_retrieval_metrics():
    ranked, relevant = ["a", "b", "c"], {"b", "c"}
    assert recall_at_k(ranked, relevant, 2) == 0.5
    assert precision_at_k(ranked, relevant, 2) == 0.5
    assert reciprocal_rank(ranked, relevant) == 0.5
    assert round(ndcg_at_k(ranked, relevant, 2), 3) == 0.387
    assert citation_coverage("Supported claim [pubmed:1]. Unsupported claim.") == 0.5


def test_clinical_trials_missing_identifier_is_skipped():
    assert parse_study({"protocolSection": {"identificationModule": {"briefTitle": "No NCT ID"}}}, "semaglutide") is None


def test_source_api_failure_does_not_stop_other_sources(database, monkeypatch):
    def failure(_drug):
        raise SourceError("timeout")
    monkeypatch.setitem(pipeline.SOURCES, "clinicaltrials.gov", failure)
    result = pipeline.ingest(database, ["semaglutide"], ["clinicaltrials.gov"])
    assert result["sources"]["clinicaltrials.gov"]["status"] == "error"
    assert "timeout" in result["sources"]["clinicaltrials.gov"]["errors"][0]["message"]


def test_raw_clinicaltrials_snapshot_can_be_imported_offline(database, tmp_path, monkeypatch):
    import pharma_intelligence.ingestion.pipeline as ingestion
    raw = tmp_path / "clinicaltrials-gov"
    raw.mkdir()
    payload = {"studies": [{"protocolSection": {
        "identificationModule": {"nctId": "NCT00000002", "briefTitle": "Offline study"},
        "statusModule": {"overallStatus": "COMPLETED"},
        "designModule": {"phases": ["PHASE3"]},
        "conditionsModule": {"conditions": ["diabetes"]},
        "armsInterventionsModule": {"interventions": [{"name": "semaglutide"}]},
    }}]}
    (raw / "20261110_semaglutide.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(ingestion, "RAW_DIR", tmp_path)
    result = ingestion.import_raw(database, ["semaglutide"])
    assert result["trials_saved"] == 1
    assert database.trials_for_drug("semaglutide")[0]["nct_id"] == "NCT00000002"


def test_timeout_from_pubmed_is_reported(monkeypatch):
    class TimeoutSession:
        def get(self, *args, **kwargs):
            import requests
            raise requests.Timeout("deliberate timeout")
    import pharma_intelligence.ingestion.pubmed as pubmed
    monkeypatch.setattr(pubmed, "session", lambda: TimeoutSession())
    with pytest.raises(SourceError, match="request failed"):
        fetch_publications("semaglutide", 1)


def test_conflict_screen_only_emits_review_flag():
    hits = [
        {"source": "pubmed", "external_id": "1", "text": "The cardiovascular outcome was significantly reduced."},
        {"source": "pubmed", "external_id": "2", "text": "There was no significant cardiovascular benefit."},
    ]
    flags = screen_conflicts(hits)
    assert len(flags) == 1
    assert "review flag only" in flags[0]


def test_golden_retrieval_dataset_has_40_queries_and_references():
    path = Path(__file__).parents[1] / "data" / "processed" / "gold_queries.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 40
    assert all(row["relevant_document_ids"] for row in rows)

