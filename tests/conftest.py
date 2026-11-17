from __future__ import annotations

import pytest

from pharma_intelligence.database.queries import ResearchDatabase


@pytest.fixture
def database(tmp_path):
    db = ResearchDatabase(tmp_path / "test.sqlite3")
    yield db
    db.close()
