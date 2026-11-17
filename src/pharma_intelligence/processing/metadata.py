from __future__ import annotations

from typing import Any

from pharma_intelligence.models import EvidenceDocument


def normalize_document(document: EvidenceDocument) -> EvidenceDocument:
    document.source = document.source.strip().lower()
    document.external_id = document.external_id.strip()
    document.title = " ".join(document.title.split())
    document.text = document.text.strip()
    document.drug_name = " ".join(document.drug_name.split())
    if not document.source or not document.external_id or not document.title or not document.text or not document.url:
        raise ValueError("Evidence documents need source, external ID, title, text, and URL")
    if not isinstance(document.metadata, dict):
        raise ValueError("Document metadata must be an object")
    return document


def json_metadata(metadata: dict[str, Any]) -> str:
    import json
    return json.dumps(metadata, sort_keys=True, ensure_ascii=False)

