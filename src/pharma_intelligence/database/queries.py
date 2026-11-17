from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from pharma_intelligence.database.models import SCHEMA
from pharma_intelligence.models import EvidenceDocument, TrialRecord
from pharma_intelligence.processing.chunking import chunk_text
from pharma_intelligence.processing.metadata import json_metadata, normalize_document
from pharma_intelligence.safety.sql_guard import install_read_only_authorizer, validate_read_only_sql


class ResearchDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def save_document(self, document: EvidenceDocument) -> None:
        document = normalize_document(document)
        doc_id = document.document_id
        with self.connection:
            self.connection.execute(
                """INSERT INTO evidence_documents
                (document_id, source, external_id, drug_name, title, text, url, published_at, metadata_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(document_id) DO UPDATE SET
                source=excluded.source, external_id=excluded.external_id, drug_name=excluded.drug_name,
                title=excluded.title, text=excluded.text, url=excluded.url,
                published_at=excluded.published_at, metadata_json=excluded.metadata_json,
                updated_at=CURRENT_TIMESTAMP""",
                (doc_id, document.source, document.external_id, document.drug_name, document.title,
                 document.text, document.url, document.published_at, json_metadata(document.metadata)),
            )
            self.connection.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))
            self.connection.executemany(
                "INSERT INTO document_chunks(document_id, ordinal, text) VALUES (?, ?, ?)",
                [(doc_id, ordinal, chunk) for ordinal, chunk in enumerate(chunk_text(document.text))],
            )

    def save_trial(self, trial: TrialRecord) -> None:
        with self.connection:
            self.connection.execute(
                """INSERT INTO trials
                (nct_id, drug_name, title, status, phase, conditions_json, interventions_json, has_results, last_update, url, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(nct_id) DO UPDATE SET
                drug_name=excluded.drug_name, title=excluded.title, status=excluded.status, phase=excluded.phase,
                conditions_json=excluded.conditions_json, interventions_json=excluded.interventions_json,
                has_results=excluded.has_results, last_update=excluded.last_update, url=excluded.url,
                ingested_at=CURRENT_TIMESTAMP""",
                (trial.nct_id, trial.drug_name, trial.title, trial.status, trial.phase,
                 json.dumps(trial.conditions), json.dumps(trial.interventions), int(trial.has_results),
                 trial.last_update, trial.url),
            )

    def save_documents(self, documents: Iterable[EvidenceDocument]) -> int:
        count = 0
        for document in documents:
            self.save_document(document)
            count += 1
        return count

    def save_trials(self, trials: Iterable[TrialRecord]) -> int:
        count = 0
        for trial in trials:
            self.save_trial(trial)
            count += 1
        return count

    def get_chunks(self, drug_names: list[str] | None = None) -> list[dict[str, Any]]:
        sql = """SELECT c.chunk_id, c.document_id, c.ordinal, c.text, d.source, d.external_id,
                 d.drug_name, d.title, d.url, d.published_at, d.metadata_json
                 FROM document_chunks c JOIN evidence_documents d ON d.document_id=c.document_id"""
        params: tuple[Any, ...] = ()
        if drug_names:
            placeholders = ",".join("?" for _ in drug_names)
            sql += f" WHERE lower(d.drug_name) IN ({placeholders})"
            params = tuple(name.lower() for name in drug_names)
        sql += " ORDER BY c.chunk_id"
        return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def search_documents(self, drug_names: list[str] | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM evidence_documents"
        params: tuple[Any, ...] = ()
        if drug_names:
            placeholders = ",".join("?" for _ in drug_names)
            sql += f" WHERE lower(drug_name) IN ({placeholders})"
            params = tuple(name.lower() for name in drug_names)
        return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def trials_for_drug(self, drug_name: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM trials WHERE lower(drug_name)=lower(?) ORDER BY nct_id", (drug_name,)
        ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["conditions"] = json.loads(item.pop("conditions_json"))
            item["interventions"] = json.loads(item.pop("interventions_json"))
            item["has_results"] = bool(item["has_results"])
            results.append(item)
        return results

    def trial_summary(self, drug_name: str) -> dict[str, Any]:
        count = self.connection.execute(
            "SELECT COUNT(*) FROM trials WHERE lower(drug_name)=lower(?)", (drug_name,)
        ).fetchone()[0]
        statuses = self.connection.execute(
            "SELECT COALESCE(status, 'Not reported') AS status, COUNT(*) AS count FROM trials "
            "WHERE lower(drug_name)=lower(?) GROUP BY status ORDER BY count DESC, status", (drug_name,)
        ).fetchall()
        phases = self.connection.execute(
            "SELECT COALESCE(phase, 'Not reported') AS phase, COUNT(*) AS count FROM trials "
            "WHERE lower(drug_name)=lower(?) GROUP BY phase ORDER BY count DESC, phase", (drug_name,)
        ).fetchall()
        with_results = self.connection.execute(
            "SELECT COUNT(*) FROM trials WHERE lower(drug_name)=lower(?) AND has_results=1", (drug_name,)
        ).fetchone()[0]
        return {
            "trial_count": count,
            "statuses": [dict(row) for row in statuses],
            "phases": [dict(row) for row in phases],
            "studies_with_results": with_results,
            "trials": self.trials_for_drug(drug_name),
        }

    def execute_read_only(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        safe_sql = validate_read_only_sql(sql)
        install_read_only_authorizer(self.connection)
        try:
            return [dict(row) for row in self.connection.execute(safe_sql, params).fetchall()]
        finally:
            self.connection.set_authorizer(None)

    def counts(self) -> dict[str, int]:
        return {
            "documents": self.connection.execute("SELECT COUNT(*) FROM evidence_documents").fetchone()[0],
            "chunks": self.connection.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0],
            "trials": self.connection.execute("SELECT COUNT(*) FROM trials").fetchone()[0],
        }

