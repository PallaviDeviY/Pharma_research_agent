from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pharma_intelligence.ingestion.clinical_trials import parse_study
from pharma_intelligence.ingestion.common import RAW_DIR
from pharma_intelligence.ingestion.openfda import parse_labels
from pharma_intelligence.ingestion.pubmed import parse_fetch_xml
from pharma_intelligence.database.queries import ResearchDatabase
from pharma_intelligence.ingestion.clinical_trials import fetch_trials
from pharma_intelligence.ingestion.common import SourceError
from pharma_intelligence.ingestion.openfda import fetch_labels
from pharma_intelligence.ingestion.pubmed import fetch_publications


SOURCES: dict[str, Callable[[str], list[Any]]] = {
    "clinicaltrials.gov": fetch_trials,
    "openfda.label": fetch_labels,
    "pubmed": fetch_publications,
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def ingest(database: ResearchDatabase, drugs: list[str], selected_sources: list[str] | None = None) -> dict[str, Any]:
    source_names = selected_sources or list(SOURCES)
    report: dict[str, Any] = {"drugs": drugs, "sources": {}, "documents_saved": 0, "trials_saved": 0}
    for source in source_names:
        fetch = SOURCES.get(source)
        if fetch is None:
            report["sources"][source] = {"status": "error", "error": "Unknown source"}
            continue
        source_result = {"status": "ok", "documents": 0, "trials": 0, "errors": []}
        for drug in drugs:
            try:
                records = fetch(drug)
                if source == "clinicaltrials.gov":
                    trials_and_docs = [item for item in records if item]
                    saved = database.save_documents([item[1] for item in trials_and_docs])
                    trial_count = database.save_trials([item[0] for item in trials_and_docs])
                    source_result["documents"] += saved
                    source_result["trials"] += trial_count
                else:
                    source_result["documents"] += database.save_documents(records)
            except (SourceError, ValueError, TypeError) as exc:
                source_result["errors"].append({"drug": drug, "message": str(exc)})
        if source_result["errors"] and source_result["documents"] == 0:
            source_result["status"] = "error"
        elif source_result["errors"]:
            source_result["status"] = "partial"
        report["documents_saved"] += source_result["documents"]
        report["trials_saved"] += source_result["trials"]
        report["sources"][source] = source_result
    report["database"] = database.counts()
    return report


def import_raw(database: ResearchDatabase, drugs: list[str]) -> dict[str, Any]:
    """Replay downloaded source responses from data/raw without calling an API."""
    result: dict[str, Any] = {"drugs": drugs, "sources": {}, "documents_saved": 0, "trials_saved": 0, "database": {}}
    source_dirs = {"clinicaltrials.gov": "clinicaltrials-gov", "openfda.label": "openfda-label", "pubmed": "pubmed"}
    for source, folder_name in source_dirs.items():
        folder = RAW_DIR / folder_name
        source_result = {"status": "empty", "documents": 0, "trials": 0, "errors": []}
        for drug in drugs:
            slug = _slug(drug)
            try:
                if source == "clinicaltrials.gov":
                    files = sorted(folder.glob(f"*{slug}*.json")) if folder.exists() else []
                    for path in files:
                        payload = json.loads(path.read_text(encoding="utf-8"))
                        studies = payload.get("studies", []) if isinstance(payload, dict) else []
                        if isinstance(payload, dict) and payload.get("protocolSection"):
                            studies = [payload]
                        pairs = [parse_study(study, drug) for study in studies if isinstance(study, dict)]
                        pairs = [pair for pair in pairs if pair]
                        source_result["documents"] += database.save_documents([pair[1] for pair in pairs])
                        source_result["trials"] += database.save_trials([pair[0] for pair in pairs])
                elif source == "openfda.label":
                    files = sorted(folder.glob(f"*{slug}*.json")) if folder.exists() else []
                    for path in files:
                        payload = json.loads(path.read_text(encoding="utf-8"))
                        source_result["documents"] += database.save_documents(parse_labels(payload, drug))
                else:
                    files = sorted(folder.glob(f"*{slug}*efetch.xml")) if folder.exists() else []
                    for path in files:
                        xml_text = path.read_text(encoding="utf-8")
                        source_result["documents"] += database.save_documents(parse_fetch_xml(xml_text, drug))
            except (OSError, json.JSONDecodeError, SourceError, ValueError, TypeError) as exc:
                source_result["errors"].append({"drug": drug, "message": str(exc)})
        if source_result["documents"] or source_result["trials"]:
            source_result["status"] = "ok" if not source_result["errors"] else "partial"
        elif source_result["errors"]:
            source_result["status"] = "error"
        result["documents_saved"] += source_result["documents"]
        result["trials_saved"] += source_result["trials"]
        result["sources"][source] = source_result
    result["database"] = database.counts()
    return result

