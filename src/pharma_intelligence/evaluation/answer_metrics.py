from __future__ import annotations

from pharma_intelligence.safety.citation_validator import citation_coverage, validate_citations


def citation_metrics(answer: str, citations: list[dict]) -> dict[str, float | int]:
    issues = validate_citations(answer, citations)
    return {
        "citation_coverage": citation_coverage(answer),
        "citation_precision": 1.0 if not issues else 0.0,
        "citation_issues": len(issues),
    }

