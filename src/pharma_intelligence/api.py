from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pharma_intelligence.agents.research_agent import DRUGS, ResearchAgent
from pharma_intelligence.config import settings
from pharma_intelligence.database.queries import ResearchDatabase
from pharma_intelligence.ingestion.pipeline import import_raw, ingest
from pharma_intelligence.safety.input_validation import InvalidResearchQuery


app = FastAPI(title="Pharma Intelligence", version="0.1.0", description="Controlled, evidence-grounded pharmaceutical research demo")
DB = ResearchDatabase(settings.database_path)
WEB_DIR = Path(__file__).resolve().parents[2] / "dashboard"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class ResearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class IngestRequest(BaseModel):
    drugs: list[str] = Field(default_factory=lambda: list(DRUGS), min_length=1, max_length=len(DRUGS))
    sources: list[str] | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status")
def status() -> dict[str, Any]:
    return {"counts": DB.counts(), "scope": list(DRUGS)}


@app.post("/api/research")
def research(request: ResearchRequest) -> dict[str, Any]:
    try:
        return ResearchAgent(DB).ask(request.question)
    except InvalidResearchQuery as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/ingest")
def refresh_sources(request: IngestRequest) -> dict[str, Any]:
    invalid_drugs = sorted(set(request.drugs) - set(DRUGS))
    if invalid_drugs:
        raise HTTPException(status_code=422, detail=f"Unsupported drug(s): {', '.join(invalid_drugs)}")
    if request.sources:
        invalid_sources = sorted(set(request.sources) - {"clinicaltrials.gov", "openfda.label", "pubmed"})
        if invalid_sources:
            raise HTTPException(status_code=422, detail=f"Unsupported source(s): {', '.join(invalid_sources)}")
    return ingest(DB, request.drugs, request.sources)


@app.post("/api/import-raw")
def import_local_sources(request: IngestRequest) -> dict[str, Any]:
    invalid_drugs = sorted(set(request.drugs) - set(DRUGS))
    if invalid_drugs:
        raise HTTPException(status_code=422, detail=f"Unsupported drug(s): {', '.join(invalid_drugs)}")
    return import_raw(DB, request.drugs)

