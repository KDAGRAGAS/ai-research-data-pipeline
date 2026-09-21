from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import duckdb


UPSERT_SQL = """
INSERT OR REPLACE INTO bronze.raw_works (
    source_record_key, doi, title, publisher, venue, work_type,
    published_date, citation_count, reference_count, subjects_json,
    authors_json, indexed_at, source_url, raw_payload, ingested_at, batch_id
) VALUES (?, ?, ?, ?, ?, ?, try_cast(? AS DATE), ?, ?, ?::JSON, ?::JSON,
          try_cast(? AS TIMESTAMPTZ), ?, ?::JSON, current_timestamp, ?)
"""


def connect(warehouse_path: Path) -> duckdb.DuckDBPyConnection:
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(warehouse_path))
    initialize(connection)
    return connection


def initialize(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    connection.execute("CREATE SCHEMA IF NOT EXISTS ops")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bronze.raw_works (
            source_record_key VARCHAR PRIMARY KEY,
            doi VARCHAR,
            title VARCHAR,
            publisher VARCHAR,
            venue VARCHAR,
            work_type VARCHAR,
            published_date DATE,
            citation_count BIGINT,
            reference_count BIGINT,
            subjects_json JSON,
            authors_json JSON,
            indexed_at TIMESTAMPTZ,
            source_url VARCHAR,
            raw_payload JSON,
            ingested_at TIMESTAMPTZ,
            batch_id VARCHAR
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.pipeline_state (
            state_key VARCHAR PRIMARY KEY,
            state_value VARCHAR,
            updated_at TIMESTAMPTZ DEFAULT current_timestamp
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.ingestion_runs (
            batch_id VARCHAR PRIMARY KEY,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            status VARCHAR,
            query VARCHAR,
            incremental_from VARCHAR,
            fetched_count BIGINT DEFAULT 0,
            inserted_count BIGINT DEFAULT 0,
            updated_count BIGINT DEFAULT 0,
            error_message VARCHAR
        )
        """
    )


def start_run(
    connection: duckdb.DuckDBPyConnection,
    batch_id: str,
    query: str,
    incremental_from: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO ops.ingestion_runs
            (batch_id, started_at, status, query, incremental_from)
        VALUES (?, current_timestamp, 'running', ?, ?)
        """,
        [batch_id, query, incremental_from],
    )


def finish_run(
    connection: duckdb.DuckDBPyConnection,
    batch_id: str,
    *,
    status: str,
    fetched: int = 0,
    inserted: int = 0,
    updated: int = 0,
    error_message: str | None = None,
) -> None:
    connection.execute(
        """
        UPDATE ops.ingestion_runs
        SET completed_at = current_timestamp,
            status = ?, fetched_count = ?, inserted_count = ?,
            updated_count = ?, error_message = ?
        WHERE batch_id = ?
        """,
        [status, fetched, inserted, updated, error_message, batch_id],
    )


def upsert_works(
    connection: duckdb.DuckDBPyConnection,
    works: Iterable[dict[str, Any]],
    batch_id: str,
) -> tuple[int, int]:
    records = list(works)
    if not records:
        return 0, 0

    keys = [record["source_record_key"] for record in records]
    existing = {
        row[0]
        for row in connection.execute(
            "SELECT source_record_key FROM bronze.raw_works WHERE source_record_key IN (SELECT unnest(?))",
            [keys],
        ).fetchall()
    }

    rows = [
        [
            record["source_record_key"],
            record["doi"],
            record["title"],
            record["publisher"],
            record["venue"],
            record["work_type"],
            record["published_date"],
            record["citation_count"],
            record["reference_count"],
            record["subjects_json"],
            record["authors_json"],
            record["indexed_at"],
            record["source_url"],
            record["raw_payload"],
            batch_id,
        ]
        for record in records
    ]
    connection.executemany(UPSERT_SQL, rows)
    updated = sum(key in existing for key in keys)
    return len(records) - updated, updated


def get_watermark(
    connection: duckdb.DuckDBPyConnection, state_key: str
) -> str | None:
    row = connection.execute(
        "SELECT state_value FROM ops.pipeline_state WHERE state_key = ?", [state_key]
    ).fetchone()
    return row[0] if row else None


def set_watermark(
    connection: duckdb.DuckDBPyConnection, state_key: str, value: str
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO ops.pipeline_state
            (state_key, state_value, updated_at)
        VALUES (?, ?, current_timestamp)
        """,
        [state_key, value],
    )


def write_raw_batch(raw_dir: Path, batch_id: str, items: list[dict[str, Any]]) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / f"crossref_{batch_id}.jsonl"
    with output_path.open("w", encoding="utf-8") as output:
        for item in items:
            output.write(json.dumps(item, ensure_ascii=False) + "\n")
    return output_path
