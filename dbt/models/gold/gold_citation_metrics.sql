select
    count(*) as paper_count,
    sum(citation_count) as total_citations,
    round(avg(citation_count), 2) as average_citations,
    median(citation_count) as median_citations,
    max(citation_count) as maximum_citations,
    round(100.0 * count(*) filter (where citation_count > 0) / nullif(count(*), 0), 2)
        as cited_paper_percentage
from {{ ref('silver_works') }}
