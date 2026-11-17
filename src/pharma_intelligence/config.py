from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("PHARMA_DB_PATH", ROOT / "data" / "pharma_intelligence.sqlite3"))
    request_timeout_seconds: float = float(os.getenv("PHARMA_REQUEST_TIMEOUT", "20"))
    max_results_per_source: int = int(os.getenv("PHARMA_MAX_RESULTS", "25"))
    vector_mode: str = os.getenv("PHARMA_VECTOR_MODE", "tfidf").lower()
    embedding_model: str = os.getenv("PHARMA_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    user_agent: str = os.getenv("PHARMA_USER_AGENT", "PharmaIntelligenceResearchDemo/0.1 (public research use)")
    ncbi_email: str | None = os.getenv("NCBI_EMAIL")
    ncbi_api_key: str | None = os.getenv("NCBI_API_KEY")
    openfda_api_key: str | None = os.getenv("OPENFDA_API_KEY")


settings = Settings()

