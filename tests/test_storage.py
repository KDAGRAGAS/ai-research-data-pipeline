import json

from ai_research_pipeline.storage import connect, upsert_works


def make_work(title: str = "First title") -> dict:
    return {
        "source_record_key": "10.1000/test",
        "doi": "10.1000/test",
        "title": title,
        "publisher": "Publisher",
        "venue": "Venue",
        "work_type": "journal-article",
        "published_date": "2025-01-01",
        "citation_count": 1,
        "reference_count": 2,
        "subjects_json": json.dumps(["AI"]),
        "authors_json": json.dumps([]),
        "indexed_at": "2025-01-02T00:00:00Z",
        "source_url": "https://doi.org/10.1000/test",
        "raw_payload": json.dumps({"DOI": "10.1000/test"}),
    }


def test_upsert_is_idempotent(tmp_path):
    connection = connect(tmp_path / "test.duckdb")
    try:
        assert upsert_works(connection, [make_work()], "batch-1") == (1, 0)
        assert upsert_works(connection, [make_work("Updated title")], "batch-2") == (0, 1)

        row = connection.execute(
            "SELECT count(*), min(title), min(batch_id) FROM bronze.raw_works"
        ).fetchone()
        assert row == (1, "Updated title", "batch-2")
    finally:
        connection.close()
