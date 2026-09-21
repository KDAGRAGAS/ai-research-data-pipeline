select doi, count(*) as duplicate_count
from {{ source('bronze', 'raw_works') }}
where doi is not null
group by doi
having count(*) > 1
