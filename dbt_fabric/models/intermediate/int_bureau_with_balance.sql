-- intermediate: join bureau + bureau_balance, deferred to Fabric Warehouse compute (ADR-003)
select
    b.SK_ID_BUREAU,
    b.SK_ID_CURR
from {{ source('silver', 'silver_bureau') }} b
