select
    *,
    trim(both ';' from concat(
        case when doi is null then 'missing_doi;' else '' end,
        case when title is null or trim(title) = '' then 'missing_title;' else '' end,
        case when published_date is null then 'missing_or_invalid_date;' else '' end,
        case when published_date is not null and year(published_date) not between 1900 and year(current_date)
             then 'date_out_of_range;' else '' end,
        case when citation_count < 0 then 'negative_citation_count;' else '' end,
        case when reference_count < 0 then 'negative_reference_count;' else '' end
    )) as quarantine_reason
from {{ source('bronze', 'raw_works') }}
where doi is null
   or title is null
   or trim(title) = ''
   or published_date is null
   or year(published_date) not between 1900 and year(current_date)
   or citation_count < 0
   or reference_count < 0
