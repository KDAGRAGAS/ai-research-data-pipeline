# Architecture and design decisions

This document explains the engineering choices behind the MVP and gives a
beginner a vocabulary for discussing them in an interview.

## End-to-end flow

1. `CrossrefClient` requests journal articles whose titles match the configured
   query. It uses retry/backoff, cursor pagination, a record safety cap, and the
   optional polite-pool email.
2. Every response item is written to a timestamped JSONL file. This is the raw,
   immutable evidence used for replay or debugging.
3. Python normalizes only commonly queried fields. The complete payload remains
   in the Bronze table as JSON, so new requirements do not require re-fetching.
4. Bronze is upserted by a stable key: lowercase DOI when available, otherwise a
   deterministic hash. Repeated delivery changes state but not row count.
5. dbt separates valid rows into Silver and invalid rows into Quarantine. It
   then explodes authors, derives venues, and creates compact Gold aggregates.
6. Python queries only built Gold/Silver models to emit `latest_metrics.json`.
   If dbt fails, no successful metrics report is produced.

## Why DuckDB

DuckDB is an embedded analytical database: there is no server to install or
cloud bill to manage. It still supports schemas, SQL analytics, JSON, date
functions, and enough scale for a strong local portfolio project. The same
layered modeling ideas later transfer to BigQuery, Snowflake, or Databricks.

## Incremental state machine

```text
no watermark ──> full/bootstrap query ──> successful commit ──> save max indexed_at
                                                          │
saved watermark ──> inclusive from-index-date query ──> upsert ──> advance watermark
                         │
                         └── failure ──> keep old watermark; log failed run
```

Only a successful load advances state. The watermark key includes a hash of the
query and publication window; each logical extraction therefore owns its state.
The inclusive boundary favors re-reading a row over missing it. Idempotent
upsert absorbs that expected duplicate delivery.

## Failure behavior

| Failure | Behavior | Why it is safe |
|---|---|---|
| API timeout/429/5xx | Retry with exponential backoff | Transient failures do not immediately abort |
| API or load failure | Mark run failed; watermark is unchanged | Next attempt resumes from last success |
| Duplicate DOI | Replace current Bronze state | One latest row per source record |
| Invalid business fields | Preserve row in Quarantine with reason | No silent data loss |
| dbt test failure | `dbt build` exits non-zero; CI fails | Bad models cannot look healthy |

## Data contracts

Bronze promises a non-null stable source key and preserved JSON payload. Silver
promises unique DOI, usable title/date, nonnegative counts, and valid author
relationships. Gold promises tested aggregate grains: one row per month, one
row per publisher, one overall citation snapshot, and one row per month/topic.

## Deliberate MVP boundaries

- `--max-records` caps learning runs; it does not claim exhaustive coverage.
- Inclusive second-level watermarks can re-read several boundary records. This
  is safe but may require narrower time windows at production volume.
- Keyword topics optimize explainability, not semantic recall.
- DuckDB supports one local writer. A production scheduler should serialize runs.
- The CI fixture tests transformation deterministically and never calls Crossref.

## Sensible next extensions

Add a dashboard only after these tables are trusted. Later steps could include
dbt documentation hosting, Slowly Changing Dimension history for citation
counts, a scheduler, partitioned Parquet exports, or a semantic topic model.
Those are intentionally outside the MVP so every current component remains easy
to explain and demonstrate.
