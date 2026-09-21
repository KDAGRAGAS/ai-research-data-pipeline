with expanded as (
    select
        works.source_record_key,
        authors.key::integer + 1 as author_position,
        json_extract_string(authors.value, '$.given') as given_name,
        json_extract_string(authors.value, '$.family') as family_name,
        json_extract_string(authors.value, '$.orcid') as orcid
    from {{ ref('silver_works') }} as works,
         json_each(works.authors_json) as authors
)

select
    md5(source_record_key || '|' || author_position::varchar) as author_record_id,
    source_record_key,
    author_position,
    nullif(trim(given_name), '') as given_name,
    nullif(trim(family_name), '') as family_name,
    nullif(trim(orcid), '') as orcid,
    trim(coalesce(given_name, '') || ' ' || coalesce(family_name, '')) as full_name
from expanded
where coalesce(given_name, family_name) is not null
