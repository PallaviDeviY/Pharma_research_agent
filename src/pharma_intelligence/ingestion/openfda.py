from __future__ import annotations

from typing import Any

import requests

from pharma_intelligence.config import settings
from pharma_intelligence.ingestion.common import SourceError, get_json, session
from pharma_intelligence.models import EvidenceDocument


BASE_URL = "https://api.fda.gov/drug/label.json"
LABEL_FIELDS = (
    "boxed_warning", "warnings", "warnings_and_cautions", "adverse_reactions",
    "indications_and_usage", "contraindications", "drug_interactions",
)


def _text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if item)
    return str(value or "")


def parse_labels(payload: dict[str, Any], drug_name: str) -> list[EvidenceDocument]:
    results = payload.get("results")
    if not isinstance(results, list):
        raise SourceError("openFDA response is missing the results list")
    documents: list[EvidenceDocument] = []
    for label in results:
        if not isinstance(label, dict):
            continue
        harmonized = label.get("openfda") or {}
        brand = _text(harmonized.get("brand_name"))
        generic = _text(harmonized.get("generic_name"))
        product = brand or generic or drug_name
        set_id = label.get("set_id") or (harmonized.get("spl_id") or [None])[0]
        if not set_id:
            # Without a stable label ID the record cannot be cited precisely.
            continue
        external_id = str(set_id)
        sections = [f"Product: {product}", f"Generic name: {generic}"]
        for field in LABEL_FIELDS:
            content = _text(label.get(field))
            if content:
                sections.append(f"{field.replace('_', ' ').title()}: {content[:12000]}")
        documents.append(EvidenceDocument(
            source="openfda.label",
            external_id=external_id,
            title=f"FDA label: {product}",
            text="\n\n".join(sections),
            url=f"https://api.fda.gov/drug/label.json?search=set_id:%22{external_id}%22",
            drug_name=drug_name,
            published_at=label.get("effective_time"),
            metadata={"set_id": set_id, "brand_name": brand, "generic_name": generic, "effective_time": label.get("effective_time")},
        ))
    return documents


def fetch_labels(drug_name: str, limit: int | None = None) -> list[EvidenceDocument]:
    query = f'openfda.generic_name:"{drug_name}" OR openfda.brand_name:"{drug_name}"'
    params: dict[str, Any] = {"search": query, "limit": min(limit or settings.max_results_per_source, 100)}
    if settings.openfda_api_key:
        params["api_key"] = settings.openfda_api_key
    try:
        payload = get_json(session(), BASE_URL, params, "openFDA", drug_name, "openfda_label")
    except SourceError as exc:
        # openFDA returns HTTP 404 when a valid search has no matches.
        if "404 Client Error" in str(exc):
            return []
        raise
    return parse_labels(payload, drug_name)

