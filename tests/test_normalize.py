from ai_research_pipeline.normalize import normalize_work


def test_normalize_work_flattens_crossref_record():
    item = {
        "DOI": "10.1000/ABC",
        "title": ["<b>Useful</b>   AI Research"],
        "container-title": ["Journal of Tests"],
        "publisher": "Test Publisher",
        "type": "journal-article",
        "published-online": {"date-parts": [[2025, 2, 3]]},
        "indexed": {"date-time": "2025-02-04T01:02:03Z"},
        "is-referenced-by-count": 4,
        "references-count": 9,
        "subject": ["Computer Science"],
        "author": [{"given": "Ada", "family": "Lovelace"}],
    }

    result = normalize_work(item)

    assert result["source_record_key"] == "10.1000/abc"
    assert result["doi"] == "10.1000/abc"
    assert result["title"] == "Useful AI Research"
    assert result["published_date"] == "2025-02-03"
    assert result["citation_count"] == 4
    assert '"family": "Lovelace"' in result["authors_json"]


def test_missing_doi_gets_a_stable_fallback_key():
    item = {
        "title": ["Same title"],
        "publisher": "Same publisher",
        "published": {"date-parts": [[2024]]},
    }

    first = normalize_work(item)
    second = normalize_work(item)

    assert first["doi"] is None
    assert first["source_record_key"] == second["source_record_key"]
    assert first["source_record_key"].startswith("missing-doi-")


def test_invalid_calendar_date_becomes_null_for_quarantine():
    item = {
        "DOI": "10.1000/bad-date",
        "title": ["Bad date"],
        "published": {"date-parts": [[2025, 13, 40]]},
    }

    assert normalize_work(item)["published_date"] is None
