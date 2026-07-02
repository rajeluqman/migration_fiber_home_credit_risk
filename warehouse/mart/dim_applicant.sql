-- grain: SK_ID_CURR — SCD Type 2 dimension, 1 row per applicant version (ADR-001)
-- Retired dbt_fabric/models/mart/dim_applicant.sql + dbt_fabric/snapshots/snap_applicant.sql
-- (ADR-008). SCD2 mechanism now: warehouse/scd2/dim_applicant_scd2_merge.sql (primary,
-- MERGE-based) with warehouse/scd2/dim_applicant_scd2_fallback.sql as the 2-step atomic
-- fallback (C5). is_current is the literal BIT column those procs maintain — the T-SQL analog
-- of a dbt snapshot's `dbt_valid_to IS NULL`.

IF NOT EXISTS (SELECT 1 FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id
               WHERE s.name = 'dbo' AND t.name = 'dim_applicant')
BEGIN
    CREATE TABLE dbo.dim_applicant (
        applicant_sk        BINARY(32)   NOT NULL,  -- HASHBYTES surrogate key (C6), NOT the match key
        applicant_id         BIGINT       NOT NULL,  -- SK_ID_CURR, SCD2 match key — identity stays applicant_id (C6)
        SK_ID_CURR            BIGINT       NOT NULL,
        name_income_type      NVARCHAR(64) NULL,
        name_education_type   NVARCHAR(64) NULL,
        name_family_status    NVARCHAR(64) NULL,
        cnt_children          INT          NULL,
        start_date            DATETIME2(7) NOT NULL,
        end_date              DATETIME2(7) NULL,
        is_current            BIT          NOT NULL
    );
END;

-- Wrapper the Data Factory Gold activity calls. Primary path = MERGE proc; point the EXEC
-- target at dbo.usp_scd2_fallback_dim_applicant instead if Fabric Warehouse MERGE proves
-- immature (Gate 1, unverified).
CREATE OR ALTER PROCEDURE dbo.usp_build_dim_applicant
AS
BEGIN
    SET NOCOUNT ON;
    EXEC dbo.usp_scd2_merge_dim_applicant;
END;
