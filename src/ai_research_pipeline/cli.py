from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ai_research_pipeline.config import PROJECT_ROOT, PipelineConfig
from ai_research_pipeline.crossref import CrossrefClient
from ai_research_pipeline.metrics import collect_metrics, write_metrics
from ai_research_pipeline.normalize import normalize_work
from ai_research_pipeline.storage import (
    connect,
    finish_run,
    get_watermark,
    set_watermark,
    start_run,
    upsert_works,
    write_raw_batch,
)


def _batch_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{uuid.uuid4().hex[:8]}"


def _watermark_key(config: PipelineConfig) -> str:
    identity = "|".join(
        [config.query, config.from_pub_date, config.until_pub_date or ""]
    ).lower()
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"crossref_indexed_at:{digest}"


def ingest(config: PipelineConfig, *, full_refresh: bool = False) -> dict[str, object]:
    connection = connect(config.warehouse_path)
    batch_id = _batch_id()
    watermark_key = _watermark_key(config)
    watermark = None if full_refresh else get_watermark(connection, watermark_key)
    start_run(connection, batch_id, config.query, watermark)

    try:
        client = CrossrefClient(mailto=config.mailto)
        raw_items = list(
            client.iter_works(
                query=config.query,
                from_pub_date=config.from_pub_date,
                until_pub_date=config.until_pub_date,
                from_index_date=watermark,
                max_records=config.max_records,
                rows_per_page=config.rows_per_page,
            )
        )
        raw_path = write_raw_batch(config.raw_dir, batch_id, raw_items)
        works = [normalize_work(item) for item in raw_items]
        inserted, updated = upsert_works(connection, works, batch_id)

        indexed_values = [work["indexed_at"] for work in works if work["indexed_at"]]
        if indexed_values:
            set_watermark(connection, watermark_key, max(indexed_values))
        finish_run(
            connection,
            batch_id,
            status="success",
            fetched=len(works),
            inserted=inserted,
            updated=updated,
        )
        connection.commit()
        return {
            "batch_id": batch_id,
            "mode": "full" if full_refresh or not watermark else "incremental",
            "watermark_used": watermark,
            "fetched": len(works),
            "inserted": inserted,
            "updated": updated,
            "raw_file": str(raw_path.relative_to(PROJECT_ROOT)),
        }
    except Exception as exc:
        finish_run(connection, batch_id, status="failed", error_message=str(exc))
        connection.commit()
        raise
    finally:
        connection.close()


def run_dbt(command: str) -> None:
    executable_name = "dbt.exe" if sys.platform == "win32" else "dbt"
    sibling_executable = Path(sys.executable).with_name(executable_name)
    dbt_executable = shutil.which("dbt") or (
        str(sibling_executable) if sibling_executable.exists() else None
    )
    if not dbt_executable:
        raise RuntimeError(
            "dbt was not found. Activate the project virtual environment and "
            "install requirements.txt."
        )
    args = [
        dbt_executable,
        command,
        "--project-dir",
        str(PROJECT_ROOT / "dbt"),
        "--profiles-dir",
        str(PROJECT_ROOT / "dbt_profiles"),
    ]
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)


def _config_from_args(args: argparse.Namespace) -> PipelineConfig:
    config = PipelineConfig.from_env()
    changes = {}
    for name in ("query", "from_pub_date", "until_pub_date", "max_records", "rows_per_page"):
        value = getattr(args, name, None)
        if value is not None:
            changes[name] = value
    return replace(config, **changes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Research Trends data pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_ingest_options(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--query")
        command_parser.add_argument("--from-pub-date")
        command_parser.add_argument("--until-pub-date")
        command_parser.add_argument("--max-records", type=int)
        command_parser.add_argument("--rows-per-page", type=int)
        command_parser.add_argument(
            "--full-refresh",
            action="store_true",
            help="Ignore the saved Crossref indexed-date watermark",
        )

    add_ingest_options(subparsers.add_parser("ingest", help="Fetch and load Crossref data"))
    add_ingest_options(subparsers.add_parser("run", help="Ingest, transform, test, and report"))
    subparsers.add_parser("metrics", help="Print verified warehouse metrics")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = _config_from_args(args)

    if args.command in {"ingest", "run"}:
        result = ingest(config, full_refresh=args.full_refresh)
        print(json.dumps(result, indent=2))
        if args.command == "run":
            run_dbt("build")

    if args.command in {"run", "metrics"}:
        metrics = collect_metrics(config.warehouse_path)
        write_metrics(metrics, PROJECT_ROOT / "reports" / "latest_metrics.json")
        print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
