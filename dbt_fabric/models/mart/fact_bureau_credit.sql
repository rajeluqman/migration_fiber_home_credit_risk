-- grain: SK_ID_BUREAU — 1 row per bureau credit record per applicant (ADR-001)
select
    SK_ID_BUREAU,
    SK_ID_CURR
from {{ source('silver', 'silver_bureau') }}
