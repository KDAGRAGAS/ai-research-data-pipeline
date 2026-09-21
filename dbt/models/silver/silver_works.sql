with source as (
    select * from {{ source('bronze', 'raw_works') }}
),

valid as (
    select
        source_record_key,
        lower(trim(doi)) as doi,
        trim(title) as title,
        coalesce(nullif(trim(publisher), ''), 'Unknown') as publisher,
        coalesce(nullif(trim(venue), ''), 'Unknown') as venue,
        work_type,
        published_date,
        citation_count,
        reference_count,
        subjects_json,
        authors_json,
        indexed_at,
        source_url,
        ingested_at,
        batch_id
    from source
    where doi is not null
      and title is not null
      and trim(title) <> ''
      and published_date is not null
      and year(published_date) between 1900 and year(current_date)
      and citation_count >= 0
      and reference_count >= 0
)

select * from valid
