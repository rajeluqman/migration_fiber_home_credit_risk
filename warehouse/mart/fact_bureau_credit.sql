-- grain: SK_ID_BUREAU — 1 row per bureau credit record per applicant (ADR-001)
-- Retired dbt_fabric/models/mart/fact_bureau_credit.sql (ADR-008).
IF NOT EXISTS (SELECT 1 FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id
               WHERE s.name = 'dbo' AND t.name = 'fact_bureau_credit')
BEGIN
    CREATE TABLE dbo.fact_bureau_credit (
        fact_bureau_credit_sk VARBINARY(32) NOT NULL,  -- HASHBYTES surrogate key (C6), not the grain key
        SK_ID_BUREAU            BIGINT     NOT NULL,  -- grain key
        SK_ID_CURR                BIGINT     NOT NULL
    );
END;

CREATE OR ALTER PROCEDURE dbo.usp_build_fact_bureau_credit
AS
BEGIN
    SET NOCOUNT ON;
    TRUNCATE TABLE dbo.fact_bureau_credit;
    INSERT INTO dbo.fact_bureau_credit (fact_bureau_credit_sk, SK_ID_BUREAU, SK_ID_CURR)
    SELECT
        CONVERT(VARBINARY(32), HASHBYTES('SHA2_256', CONVERT(VARCHAR(20), ISNULL(SK_ID_BUREAU, -1)))),
        SK_ID_BUREAU,
        SK_ID_CURR
    FROM dbo.int_bureau_with_balance;

    EXEC dbo.usp_assert_fact_bureau_credit_grain;
END;
