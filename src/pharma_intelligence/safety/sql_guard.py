from __future__ import annotations

import re
import sqlite3


class UnsafeQueryError(ValueError):
    pass


FORBIDDEN = re.compile(
    r"\b(insert|update|delete|replace|create|alter|drop|attach|detach|pragma|vacuum|reindex|"
    r"begin|commit|rollback|savepoint|release|load_extension|grant|revoke|truncate)\b",
    re.IGNORECASE,
)
COMMENT = re.compile(r"(--[^\n]*|/\*[\s\S]*?\*/)")


def validate_read_only_sql(sql: str) -> str:
    cleaned = COMMENT.sub(" ", sql or "").strip()
    if not cleaned or not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise UnsafeQueryError("Only a single read-only SELECT query is allowed")
    if ";" in cleaned.rstrip(";"):
        raise UnsafeQueryError("Multiple SQL statements are not allowed")
    if FORBIDDEN.search(cleaned):
        raise UnsafeQueryError("The query contains a write or privileged SQL operation")
    if cleaned.count(";") > 1:
        raise UnsafeQueryError("Multiple SQL statements are not allowed")
    return cleaned.rstrip(";").strip()


def install_read_only_authorizer(connection: sqlite3.Connection) -> None:
    """Prevent writes even if a query string slips past lexical validation."""
    allowed = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_RECURSIVE,
    }

    def authorizer(action: int, arg1: str | None, arg2: str | None, db_name: str | None, trigger: str | None) -> int:
        return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

    connection.set_authorizer(authorizer)

