"""SQLite schema used for the reproducible local demo; portable SQL types ease PostgreSQL migration."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_documents (
    document_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    drug_name TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_documents_source ON evidence_documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_drug ON evidence_documents(drug_name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL REFERENCES evidence_documents(document_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    UNIQUE(document_id, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);

CREATE TABLE IF NOT EXISTS trials (
    nct_id TEXT PRIMARY KEY,
    drug_name TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT,
    phase TEXT,
    conditions_json TEXT NOT NULL DEFAULT '[]',
    interventions_json TEXT NOT NULL DEFAULT '[]',
    has_results INTEGER NOT NULL DEFAULT 0,
    last_update TEXT,
    url TEXT NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_trials_drug ON trials(drug_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_trials_status ON trials(status);
"""
