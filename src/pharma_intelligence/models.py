from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceDocument:
    source: str
    external_id: str
    title: str
    text: str
    url: str
    drug_name: str = ""
    published_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def document_id(self) -> str:
        return f"{self.source}:{self.external_id}"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["document_id"] = self.document_id
        return result


@dataclass
class TrialRecord:
    nct_id: str
    title: str
    status: str | None
    phase: str | None
    conditions: list[str]
    interventions: list[str]
    has_results: bool
    last_update: str | None
    url: str
    drug_name: str


@dataclass
class ResearchReport:
    question: str
    answer: str
    citations: list[dict[str, str]]
    evidence: list[dict[str, Any]]
    limitations: list[str]
    conflicts: list[str]
    abstained: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

