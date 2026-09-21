"""Load a tiny deterministic dataset so CI can test dbt without calling Crossref."""

from ai_research_pipeline.config import PipelineConfig
from ai_research_pipeline.normalize import normalize_work
from ai_research_pipeline.storage import connect, upsert_works


ITEMS = [
    {
        "DOI": "10.5555/fixture-1",
        "title": ["A machine learning benchmark"],
        "container-title": ["Fixture Journal"],
        "publisher": "Fixture Press",
        "type": "journal-article",
        "published": {"date-parts": [[2025, 1, 15]]},
        "indexed": {"date-time": "2025-01-20T00:00:00Z"},
        "is-referenced-by-count": 3,
        "references-count": 10,
        "author": [{"given": "Test", "family": "Author"}],
    },
    {
        "DOI": "10.5555/fixture-invalid",
        "title": [],
        "publisher": "Fixture Press",
        "type": "journal-article",
        "published": {"date-parts": [[2025, 1, 16]]},
        "indexed": {"date-time": "2025-01-20T00:00:00Z"},
    },
]


def main() -> None:
    connection = connect(PipelineConfig.from_env().warehouse_path)
    try:
        upsert_works(connection, [normalize_work(item) for item in ITEMS], "ci-fixture")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
