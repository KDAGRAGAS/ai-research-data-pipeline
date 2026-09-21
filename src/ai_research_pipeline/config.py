from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class PipelineConfig:
    query: str = "artificial intelligence"
    from_pub_date: str = "2024-01-01"
    until_pub_date: str | None = None
    max_records: int = 100
    rows_per_page: int = 50
    mailto: str | None = None
    warehouse_path: Path = PROJECT_ROOT / "data" / "warehouse.duckdb"
    raw_dir: Path = PROJECT_ROOT / "data" / "raw"

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        warehouse = Path(os.getenv("WAREHOUSE_PATH", "data/warehouse.duckdb"))
        if not warehouse.is_absolute():
            warehouse = PROJECT_ROOT / warehouse

        mailto = os.getenv("CROSSREF_MAILTO")
        if mailto and mailto == "your-email@example.com":
            mailto = None

        return cls(
            query=os.getenv("CROSSREF_QUERY", "artificial intelligence"),
            from_pub_date=os.getenv("CROSSREF_FROM_PUB_DATE", "2024-01-01"),
            until_pub_date=os.getenv("CROSSREF_UNTIL_PUB_DATE") or None,
            max_records=int(os.getenv("CROSSREF_MAX_RECORDS", "100")),
            rows_per_page=int(os.getenv("CROSSREF_ROWS_PER_PAGE", "50")),
            mailto=mailto,
            warehouse_path=warehouse,
            raw_dir=PROJECT_ROOT / "data" / "raw",
        )
