from __future__ import annotations

import re
from urllib.parse import urlparse
from typing import Any


CITATION_PATTERN = re.compile(r"\[((?:clinicaltrials\.gov|openfda\.label|pubmed):[A-Za-z0-9._-]+)\]")
ALLOWED_HOSTS = {
    "clinicaltrials.gov", "api.fda.gov", "open.fda.gov", "pubmed.ncbi.nlm.nih.gov",
}


def validate_citations(answer: str, citations: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    by_id = {item.get("id"): item for item in citations if item.get("id")}
    for reference in CITATION_PATTERN.findall(answer or ""):
        if reference not in by_id:
            issues.append(f"Answer refers to missing citation {reference}.")
    for citation in citations:
        parsed = urlparse(str(citation.get("url", "")))
        if parsed.scheme != "https" or not any(parsed.hostname == host or (parsed.hostname or "").endswith("." + host) for host in ALLOWED_HOSTS):
            issues.append(f"Citation {citation.get('id', '(unknown)')} has a non-approved source URL.")
        if not citation.get("id") or not citation.get("title"):
            issues.append("A citation is missing its source ID or title.")
    return issues


def citation_coverage(answer: str) -> float:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", answer or "") if part.strip()]
    if not sentences:
        return 1.0
    supported = sum(1 for sentence in sentences if CITATION_PATTERN.search(sentence))
    return supported / len(sentences)

