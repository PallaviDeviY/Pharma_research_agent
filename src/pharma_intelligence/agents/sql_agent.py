from __future__ import annotations

from typing import Any

from pharma_intelligence.database.queries import ResearchDatabase


class SQLAgent:
    """Read-only structured trial tool; user text is always a bound parameter."""

    def __init__(self, database: ResearchDatabase):
        self.database = database

    def trial_landscape(self, drug_name: str) -> dict[str, Any]:
        return self.database.trial_summary(drug_name)

