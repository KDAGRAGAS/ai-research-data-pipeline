select *
from {{ ref('gold_papers_by_month') }}
where paper_count < 0
   or total_citations < 0
   or average_citations < 0
