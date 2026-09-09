"""The embedded DuckDB warehouse connection."""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import duckdb

_SCHEMA_RESOURCE = importlib.resources.files("analytics.db") / "schema.sql"


def connect(path: str | Path) -> duckdb.DuckDBPyConnection:
    """Open the warehouse file, creating it and its schema if it does not exist.

    Safe to call repeatedly: every statement in schema.sql is idempotent
    (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).
    """
    conn = duckdb.connect(str(path))
    apply_schema(conn)
    return conn


def apply_schema(conn: duckdb.DuckDBPyConnection) -> None:
    ddl = _SCHEMA_RESOURCE.read_text(encoding="utf-8")
    conn.execute(ddl)


def next_surrogate_key(conn: duckdb.DuckDBPyConnection, table: str, key_column: str) -> int:
    """Return the next surrogate key for `table`.

    Surrogate keys are assigned here because the schema deliberately avoids
    database-specific identity syntax.
    """
    (current_max,) = conn.execute(f"SELECT MAX({key_column}) FROM {table}").fetchone()
    return (current_max or 0) + 1
