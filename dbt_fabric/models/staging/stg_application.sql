-- staging: clean + cast application_train, T-SQL dialect (no QUALIFY — Fabric Warehouse)
select
    SK_ID_CURR as applicant_id,
    SK_ID_CURR,
    NAME_INCOME_TYPE as name_income_type,
    NAME_EDUCATION_TYPE as name_education_type,
    NAME_FAMILY_STATUS as name_family_status,
    CNT_CHILDREN as cnt_children,
    ingestion_ts,
    ingestion_date
from {{ source('silver', 'silver_application') }}
where SK_ID_CURR is not null
