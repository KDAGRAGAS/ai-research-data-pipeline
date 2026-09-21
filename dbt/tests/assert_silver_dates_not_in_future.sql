select *
from {{ ref('silver_works') }}
where published_date > current_date
