from __future__ import annotations

from typing import Any

from pharma_intelligence.models import ResearchReport
from pharma_intelligence.agents.conflict_screen import screen_conflicts
from pharma_intelligence.safety.citation_validator import validate_citations
from pharma_intelligence.safety.prompt_injection import filter_retrieved_text


class SynthesisAgent:
    """Conservative deterministic synthesis: claims are rendered from fetched fields/snippets."""

    def build(self, question: str, drugs: list[str], landscapes: dict[str, dict[str, Any]], hits: list[dict[str, Any]]) -> ResearchReport:
        citations_by_id: dict[str, dict[str, str]] = {}
        evidence: list[dict[str, Any]] = []
        answer_parts: list[str] = []
        limitations = [
            "Trial counts describe this local ingestion snapshot only; each source fetch is capped by the configured result limit.",
            "Evidence types answer different questions. Spontaneous adverse-event reports, if added later, must not be treated as proof of causation.",
            "This baseline screens for evidence and produces deterministic summaries; it does not provide diagnosis or treatment advice.",
        ]

        for drug in drugs:
            summary = landscapes.get(drug, {"trial_count": 0, "trials": [], "statuses": [], "phases": [], "studies_with_results": 0})
            trial_citations = []
            for trial in summary.get("trials", []):
                citation_id = f"clinicaltrials.gov:{trial['nct_id']}"
                cite = {"id": citation_id, "url": trial["url"], "title": trial["title"], "source": "clinicaltrials.gov"}
                citations_by_id[citation_id] = cite
                trial_citations.append(citation_id)
            if summary.get("trial_count", 0):
                status_counts = ", ".join(f"{row['status']}: {row['count']}" for row in summary.get("statuses", [])) or "not reported"
                phase_counts = ", ".join(f"{row['phase']}: {row['count']}" for row in summary.get("phases", [])) or "not reported"
                cite_text = " ".join(f"[{item}]" for item in trial_citations)
                answer_parts.append(
                    f"For **{drug}**, the local registry snapshot contains {summary['trial_count']} retrieved trial record(s). "
                    f"{cite_text} Reported status counts are {status_counts}; phase counts are {phase_counts}; "
                    f"{summary.get('studies_with_results', 0)} record(s) include a results section. {cite_text}"
                )
            else:
                answer_parts.append(f"No trial records for **{drug}** are currently stored in this local database.")

        for hit in hits:
            source = hit["source"]
            citation_id = f"{source}:{hit['external_id']}"
            citations_by_id[citation_id] = {"id": citation_id, "url": hit["url"], "title": hit["title"], "source": source}
            safe_text, injection_removed = filter_retrieved_text(hit["text"])
            words = safe_text.split()
            snippet = " ".join(words[:75])
            if len(words) > 75:
                snippet += " …"
            if not snippet:
                snippet = "Instruction-like text was omitted from this source excerpt."
            evidence.append({
                "citation_id": citation_id,
                "source": source,
                "title": hit["title"],
                "url": hit["url"],
                "drug_name": hit["drug_name"],
                "excerpt": snippet,
                "relevance_score": round(float(hit.get("rerank_score", 0)), 4),
                "safety_flags": ["instruction-like text omitted from excerpt"] if injection_removed else [],
            })
            answer_parts.append(f"Retrieved {source} evidence **{hit['title']}**: “{snippet}” [{citation_id}]")

        safe_hits = [dict(hit, text=filter_retrieved_text(hit["text"])[0]) for hit in hits]
        conflicts = screen_conflicts(safe_hits)

        if not hits and not any(landscapes.get(drug, {}).get("trial_count", 0) for drug in drugs):
            return ResearchReport(
                question=question,
                answer="I don't have sufficient ingested evidence to answer this question. Refresh the selected public sources or narrow the question to a supported drug.",
                citations=[], evidence=[], limitations=limitations,
                conflicts=[], abstained=True,
            )
        if not hits:
            limitations.append("No matching label or publication chunks were retrieved for this wording; the answer relies on registry fields only.")
        answer = "\n\n".join(answer_parts)
        issues = validate_citations(answer, list(citations_by_id.values()))
        if issues:
            return ResearchReport(
                question=question,
                answer="I could not validate the source links for a safe answer, so I am abstaining. Please refresh the source records and try again.",
                citations=[], evidence=[], limitations=limitations + issues,
                conflicts=[], abstained=True,
            )
        return ResearchReport(question, answer, list(citations_by_id.values()), evidence, limitations, conflicts, False)

