from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import date
from typing import Any


TAG_RE = re.compile(r"<[^>]+>")


def _first(values: Any) -> str | None:
    if not isinstance(values, list) or not values:
        return None
    value = values[0]
    return str(value).strip() if value is not None else None


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = TAG_RE.sub(" ", html.unescape(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def _date_from_parts(item: dict[str, Any]) -> str | None:
    for field in ("published-print", "published-online", "published"):
        parts = item.get(field, {}).get("date-parts", [])
        if not parts or not parts[0]:
            continue
        values = parts[0]
        year = int(values[0])
        month = int(values[1]) if len(values) > 1 else 1
        day = int(values[2]) if len(values) > 2 else 1
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def normalize_work(item: dict[str, Any]) -> dict[str, Any]:
    """Flatten the useful fields while preserving the complete source payload."""
    doi = str(item.get("DOI", "")).strip().lower() or None
    title = _clean_text(_first(item.get("title")))
    venue = _clean_text(_first(item.get("container-title")))
    publisher = _clean_text(item.get("publisher"))
    indexed_at = item.get("indexed", {}).get("date-time")

    authors = []
    for author in item.get("author") or []:
        authors.append(
            {
                "given": _clean_text(author.get("given")),
                "family": _clean_text(author.get("family")),
                "orcid": author.get("ORCID"),
            }
        )

    fallback_identity = "|".join(
        [title or "", publisher or "", _date_from_parts(item) or ""]
    ).lower()
    source_record_key = doi or "missing-doi-" + hashlib.sha256(
        fallback_identity.encode("utf-8")
    ).hexdigest()[:24]

    return {
        "source_record_key": source_record_key,
        "doi": doi,
        "title": title,
        "publisher": publisher,
        "venue": venue,
        "work_type": item.get("type"),
        "published_date": _date_from_parts(item),
        "citation_count": int(item.get("is-referenced-by-count") or 0),
        "reference_count": int(item.get("references-count") or 0),
        "subjects_json": json.dumps(item.get("subject") or [], ensure_ascii=False),
        "authors_json": json.dumps(authors, ensure_ascii=False),
        "indexed_at": indexed_at,
        "source_url": item.get("URL"),
        "raw_payload": json.dumps(item, ensure_ascii=False),
    }
