with matches as (
    select
        date_trunc('month', works.published_date)::date as publication_month,
        topics.topic,
        works.source_record_key,
        works.citation_count
    from {{ ref('silver_works') }} as works
    cross join {{ ref('ai_topics') }} as topics
    where lower(works.title) like '%' || lower(topics.keyword) || '%'
)

select
    publication_month,
    topic,
    count(distinct source_record_key) as paper_count,
    sum(citation_count) as total_citations
from matches
group by publication_month, topic
order by publication_month, paper_count desc, topic
