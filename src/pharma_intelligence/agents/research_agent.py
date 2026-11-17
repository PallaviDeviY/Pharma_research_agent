from __future__ import annotations

import re
from typing import Any

from pharma_intelligence.agents.evidence_agent import EvidenceAgent
from pharma_intelligence.agents.sql_agent import SQLAgent
from pharma_intelligence.agents.synthesis_agent import SynthesisAgent
from pharma_intelligence.database.queries import ResearchDatabase
from pharma_intelligence.models import ResearchReport
from pharma_intelligence.safety.input_validation import is_personal_medical_advice, validate_question


DRUGS = {
    "semaglutide": ("semaglutide", "ozempic", "wegovy", "rybelsus"),
    "empagliflozin": ("empagliflozin", "jardiance"),
    "dapagliflozin": ("dapagliflozin", "farxiga", "forxiga"),
    "liraglutide": ("liraglutide", "victoza", "saxenda"),
}


def identify_drugs(question: str) -> list[str]:
    lowered = question.casefold()
    found = []
    for generic, names in DRUGS.items():
        if any(re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", lowered) for name in names):
            found.append(generic)
    return found


class ResearchAgent:
    """Small controlled workflow with a SQL tool, evidence retriever, and grounded synthesizer."""

    def __init__(self, database: ResearchDatabase):
        self.database = database
        self.sql_agent = SQLAgent(database)
        self.evidence_agent = EvidenceAgent(database)
        self.synthesis_agent = SynthesisAgent()

    def ask(self, question: str) -> dict[str, Any]:
        question = validate_question(question)
        if is_personal_medical_advice(question):
            return ResearchReport(
                question=question,
                answer="I can summarize published and regulatory evidence, but I can't advise on personal treatment or dosing. Please ask a licensed clinician or pharmacist.",
                citations=[], evidence=[],
                limitations=["This research tool is not for individual diagnosis or treatment decisions."],
                conflicts=[], abstained=True,
            ).to_dict()
        drugs = identify_drugs(question)
        if not drugs:
            return ResearchReport(
                question=question,
                answer="I couldn't identify a supported drug in the current research scope. Try semaglutide, empagliflozin, dapagliflozin, or liraglutide.",
                citations=[], evidence=[],
                limitations=["The controlled demo corpus currently covers four drugs."],
                conflicts=[], abstained=True,
            ).to_dict()

        # Fixed SELECT templates plus bound parameters prevent user text from becoming SQL.
        landscapes = {drug: self.sql_agent.trial_landscape(drug) for drug in drugs}
        hits = self.evidence_agent.retrieve(question, drugs)
        return self.synthesis_agent.build(question, drugs, landscapes, hits).to_dict()

