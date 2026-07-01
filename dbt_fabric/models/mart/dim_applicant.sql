-- grain: SK_ID_CURR — SCD Type 2 dimension, 1 row per applicant version (ADR-001)
select
    applicant_id,
    SK_ID_CURR,
    name_income_type,
    name_education_type,
    name_family_status,
    cnt_children,
    dbt_valid_from as start_date,
    dbt_valid_to as end_date,
    case when dbt_valid_to is null then true else false end as is_current
from {{ ref('snap_applicant') }}
