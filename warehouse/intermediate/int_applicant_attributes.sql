-- intermediate: feeds the dim_applicant SCD2 build, 1:1 pass-through from staging
-- Retired dbt_fabric/models/intermediate/int_applicant_attributes.sql (ADR-008).
CREATE OR ALTER VIEW dbo.int_applicant_attributes AS
SELECT
    applicant_id,
    SK_ID_CURR,
    name_income_type,
    name_education_type,
    name_family_status,
    cnt_children,
    ingestion_ts,
    ingestion_date
FROM dbo.stg_application;
