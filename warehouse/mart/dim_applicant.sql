-- grain: SK_ID_CURR — SCD Type 2 dimension, 1 row per applicant version (ADR-001)
-- Retired dbt_fabric/models/mart/dim_applicant.sql + dbt_fabric/snapshots/snap_applicant.sql
-- (ADR-008). SCD2 mechanism: warehouse/scd2/dim_applicant_scd2_fallback.sql (sole mechanism —
-- the MERGE-based proc is retired, J-021: Fabric Warehouse does not support the OUTPUT clause
-- on any statement, so the MERGE...OUTPUT...INTO @touched design is structurally impossible on
-- this engine, not merely immature; see @data-architect verdict,
-- migration/governance/GATE3_ARCHITECT_REVIEW_J021.md). is_current is the literal BIT column
-- that proc maintains — the T-SQL analog of a dbt snapshot's `dbt_valid_to IS NULL`.
-- Column types VARBINARY/VARCHAR/DATETIME2(6) (not BINARY/NVARCHAR/DATETIME2(7)) per J-021
-- findings 1-3 (Fabric Warehouse does not support BINARY, NVARCHAR under its UTF-8 collation,
-- or DATETIME2 precision above 6).

IF NOT EXISTS (SELECT 1 FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id
               WHERE s.name = 'dbo' AND t.name = 'dim_applicant')
BEGIN
    CREATE TABLE dbo.dim_applicant (
        applicant_sk        VARBINARY(32) NOT NULL,  -- HASHBYTES surrogate key (C6), NOT the match key
        applicant_id         BIGINT       NOT NULL,  -- SK_ID_CURR, SCD2 match key — identity stays applicant_id (C6)
        SK_ID_CURR            BIGINT       NOT NULL,
        name_income_type      VARCHAR(64)  NULL,
        name_education_type   VARCHAR(64)  NULL,
        name_family_status    VARCHAR(64)  NULL,
        cnt_children          INT          NULL,
        start_date            DATETIME2(6) NOT NULL,
        end_date              DATETIME2(6) NULL,
        is_current            BIT          NOT NULL
    );
END;

-- Wrapper the Data Factory Gold activity calls. Sole path = the 2-step fallback proc (J-021 —
-- the MERGE proc is retired, not merely deprioritized).
CREATE OR ALTER PROCEDURE dbo.usp_build_dim_applicant
AS
BEGIN
    SET NOCOUNT ON;
    EXEC dbo.usp_scd2_fallback_dim_applicant;
END;
