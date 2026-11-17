from __future__ import annotations

from typing import Any

from pharma_intelligence.config import settings
from pharma_intelligence.ingestion.common import SourceError, get_json, session
from pharma_intelligence.models import EvidenceDocument, TrialRecord


BASE_URL = "https://clinicaltrials.gov/api/v2/studies"


def _join(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return "; ".join(str(v) for v in values if v)


def parse_study(study: dict[str, Any], drug_name: str) -> tuple[TrialRecord, EvidenceDocument] | None:
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    nct_id = identification.get("nctId")
    if not nct_id:
        return None

    status_module = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    interventions_module = protocol.get("armsInterventionsModule") or {}
    conditions_module = protocol.get("conditionsModule") or {}
    description = protocol.get("descriptionModule") or {}
    outcomes = protocol.get("outcomesModule") or {}
    results = study.get("resultsSection") or {}
    interventions = [
        item.get("name", "") for item in interventions_module.get("interventions", [])
        if isinstance(item, dict) and item.get("name")
    ]
    conditions = conditions_module.get("conditions", []) or []
    phases = design.get("phases", []) or []
    title = identification.get("briefTitle") or identification.get("officialTitle") or nct_id
    status = status_module.get("overallStatus")
    phase = _join(phases) or None
    last_update = (status_module.get("studyLastUpdatePostDateStruct") or {}).get("date")
    record = TrialRecord(
        nct_id=nct_id,
        title=title,
        status=status,
        phase=phase,
        conditions=conditions if isinstance(conditions, list) else [],
        interventions=interventions,
        has_results=bool(results),
        last_update=last_update,
        url=f"https://clinicaltrials.gov/study/{nct_id}",
        drug_name=drug_name,
    )

    paragraphs = [title]
    for label, value in (
        ("Brief summary", description.get("briefSummary")),
        ("Detailed description", description.get("detailedDescription")),
        ("Conditions", _join(conditions)),
        ("Interventions", _join(interventions)),
        ("Phase", phase),
        ("Study status", status),
        ("Primary outcomes", "; ".join(
            str(o.get("measure", "")) for o in outcomes.get("primaryOutcomes", []) if isinstance(o, dict)
        )),
    ):
        if value:
            paragraphs.append(f"{label}: {value}")
    document = EvidenceDocument(
        source="clinicaltrials.gov",
        external_id=nct_id,
        title=title,
        text="\n".join(paragraphs),
        url=record.url,
        drug_name=drug_name,
        published_at=last_update,
        metadata={"status": status, "phase": phase, "conditions": conditions, "interventions": interventions, "has_results": bool(results)},
    )
    return record, document


def fetch_trials(drug_name: str, limit: int | None = None) -> list[tuple[TrialRecord, EvidenceDocument]]:
    client = session()
    payload = get_json(client, BASE_URL, {
        "format": "json",
        "query.intr": drug_name,
        "pageSize": min(limit or settings.max_results_per_source, 100),
        "sort": "StudyFirstPostDate:desc",
    }, "ClinicalTrials.gov", drug_name, "clinicaltrials_gov")
    studies = payload.get("studies")
    if not isinstance(studies, list):
        raise SourceError("ClinicalTrials.gov response is missing the studies list")
    parsed = [parse_study(study, drug_name) for study in studies if isinstance(study, dict)]
    return [item for item in parsed if item is not None]

