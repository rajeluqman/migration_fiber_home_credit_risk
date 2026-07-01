-- intermediate: feeds snap_applicant snapshot, 1:1 pass-through from staging
select
    applicant_id,
    SK_ID_CURR,
    name_income_type,
    name_education_type,
    name_family_status,
    cnt_children,
    ingestion_ts,
    ingestion_date
from {{ ref('stg_application') }}
