from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def collect_metrics(warehouse_path: Path) -> dict[str, Any]:
    connection = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        count_queries = {
            "bronze_records": "SELECT count(*) FROM bronze.raw_works",
            "silver_valid_works": "SELECT count(*) FROM silver.silver_works",
            "quarantined_records": "SELECT count(*) FROM quarantine.quarantine_works",
            "silver_authors": "SELECT count(*) FROM silver.silver_authors",
            "gold_month_rows": "SELECT count(*) FROM gold.gold_papers_by_month",
            "gold_topic_month_rows": "SELECT count(*) FROM gold.gold_topic_trends",
        }
        result = {
            name: connection.execute(query).fetchone()[0]
            for name, query in count_queries.items()
        }
        window = connection.execute(
            "SELECT min(published_date), max(published_date) FROM silver.silver_works"
        ).fetchone()
        result["publication_window"] = {"from": window[0], "to": window[1]}

        citation_row = connection.execute(
            "SELECT * FROM gold.gold_citation_metrics"
        ).fetchone()
        result["citation_metrics"] = dict(
            zip(
                [
                    "paper_count",
                    "total_citations",
                    "average_citations",
                    "median_citations",
                    "maximum_citations",
                    "cited_paper_percentage",
                ],
                citation_row,
            )
        )

        publisher_rows = connection.execute(
            """
            SELECT publisher, paper_count, total_citations
            FROM gold.gold_top_publishers
            ORDER BY paper_count DESC, total_citations DESC, publisher
            LIMIT 5
            """
        ).fetchall()
        result["top_publishers"] = [
            {"publisher": row[0], "paper_count": row[1], "total_citations": row[2]}
            for row in publisher_rows
        ]

        topic_rows = connection.execute(
            """
            SELECT topic, sum(paper_count)::bigint AS paper_count
            FROM gold.gold_topic_trends
            GROUP BY topic
            ORDER BY paper_count DESC, topic
            """
        ).fetchall()
        result["topic_totals"] = [
            {"topic": row[0], "paper_count": row[1]} for row in topic_rows
        ]

        ingestion_row = connection.execute(
            """
            SELECT batch_id, status, fetched_count, inserted_count, updated_count,
                   completed_at
            FROM ops.ingestion_runs
            ORDER BY started_at DESC LIMIT 1
            """
        ).fetchone()
        result["latest_ingestion"] = dict(
            zip(
                [
                    "batch_id",
                    "status",
                    "fetched_count",
                    "inserted_count",
                    "updated_count",
                    "completed_at",
                ],
                ingestion_row,
            )
        )
        result["generated_at"] = datetime.now().astimezone().isoformat()
        return result
    finally:
        connection.close()


def write_metrics(metrics: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )
