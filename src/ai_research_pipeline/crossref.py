from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://api.crossref.org/works"
SELECT_FIELDS = ",".join(
    [
        "DOI",
        "title",
        "container-title",
        "publisher",
        "type",
        "published",
        "published-print",
        "published-online",
        "indexed",
        "is-referenced-by-count",
        "references-count",
        "subject",
        "author",
        "URL",
    ]
)


class CrossrefClient:
    """Small, retry-aware client for the public Crossref REST API."""

    def __init__(self, mailto: str | None = None, timeout_seconds: int = 30):
        self.mailto = mailto
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        user_agent = "ai-research-data-pipeline/0.1"
        if mailto:
            user_agent += f" (mailto:{mailto})"
        self.session.headers.update({"User-Agent": user_agent})

    def iter_works(
        self,
        *,
        query: str,
        from_pub_date: str,
        until_pub_date: str | None,
        from_index_date: str | None,
        max_records: int,
        rows_per_page: int,
    ) -> Iterator[dict[str, Any]]:
        """Yield works using cursor pagination, stopping at max_records."""
        if max_records < 1:
            return

        filters = ["type:journal-article", f"from-pub-date:{from_pub_date}"]
        if until_pub_date:
            filters.append(f"until-pub-date:{until_pub_date}")
        if from_index_date:
            # Crossref payloads use a trailing UTC "Z", while its date-filter
            # grammar accepts timestamps through seconds without a zone suffix.
            filters.append(f"from-index-date:{from_index_date.rstrip('Z')}")

        cursor = "*"
        yielded = 0
        page_size = min(max(1, rows_per_page), 1000, max_records)

        while yielded < max_records:
            params = {
                "query.title": query,
                "filter": ",".join(filters),
                "select": SELECT_FIELDS,
                # Oldest indexed records first lets capped demo runs advance the
                # watermark predictably instead of jumping to a recent record.
                "sort": "indexed",
                "order": "asc",
                "rows": min(page_size, max_records - yielded),
                "cursor": cursor,
            }
            if self.mailto:
                params["mailto"] = self.mailto

            response = self.session.get(
                BASE_URL, params=params, timeout=self.timeout_seconds
            )
            response.raise_for_status()
            message = response.json()["message"]
            items = message.get("items", [])
            if not items:
                break

            for item in items:
                yield item
                yielded += 1
                if yielded >= max_records:
                    break

            next_cursor = message.get("next-cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
