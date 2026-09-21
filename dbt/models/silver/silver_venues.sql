select
    md5(lower(venue) || '|' || lower(publisher)) as venue_id,
    venue,
    publisher,
    count(*) as paper_count,
    min(published_date) as first_publication_date,
    max(published_date) as latest_publication_date
from {{ ref('silver_works') }}
group by venue, publisher
