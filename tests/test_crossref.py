from ai_research_pipeline.crossref import CrossrefClient


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"message": {"items": [], "next-cursor": None}}


class FakeSession:
    def __init__(self):
        self.params = None

    def get(self, _url, *, params, timeout):
        self.params = params
        return FakeResponse()


def test_incremental_timestamp_is_formatted_for_crossref_filter():
    client = CrossrefClient()
    fake_session = FakeSession()
    client.session = fake_session

    list(
        client.iter_works(
            query="artificial intelligence",
            from_pub_date="2024-01-01",
            until_pub_date=None,
            from_index_date="2024-01-18T00:28:44Z",
            max_records=1,
            rows_per_page=1,
        )
    )

    assert "from-index-date:2024-01-18T00:28:44" in fake_session.params["filter"]
    assert fake_session.params["query.title"] == "artificial intelligence"
    assert fake_session.params["sort"] == "indexed"
    assert fake_session.params["order"] == "asc"
