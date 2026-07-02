-- staging: clean + cast application_train, T-SQL dialect (no QUALIFY — Fabric Warehouse)
-- Retired dbt_fabric/models/staging/stg_application.sql (ADR-008) — same shape, no dbt.
CREATE OR ALTER VIEW dbo.stg_application AS
SELECT
    SK_ID_CURR                        AS applicant_id,
    SK_ID_CURR,
    NAME_INCOME_TYPE                  AS name_income_type,
    NAME_EDUCATION_TYPE                AS name_education_type,
    NAME_FAMILY_STATUS                 AS name_family_status,
    CNT_CHILDREN                       AS cnt_children,
    ingestion_ts,
    ingestion_date
FROM silver.silver_application
WHERE SK_ID_CURR IS NOT NULL;
