select
    date_trunc('month', published_date)::date as publication_month,
    count(*) as paper_count,
    sum(citation_count) as total_citations,
    round(avg(citation_count), 2) as average_citations
from {{ ref('silver_works') }}
group by 1
order by 1
