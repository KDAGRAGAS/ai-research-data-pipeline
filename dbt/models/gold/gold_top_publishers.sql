select
    publisher,
    count(*) as paper_count,
    sum(citation_count) as total_citations,
    round(avg(citation_count), 2) as average_citations,
    count(distinct venue) as venue_count
from {{ ref('silver_works') }}
group by publisher
order by paper_count desc, total_citations desc, publisher
