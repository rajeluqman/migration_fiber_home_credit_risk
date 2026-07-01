-- grain: SK_ID_CURR — 1 row per loan application (ADR-001)
select
    SK_ID_CURR,
    applicant_id
from {{ ref('stg_application') }}
