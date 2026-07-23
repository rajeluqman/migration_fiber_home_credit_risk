-- grain: SK_ID_CURR — 1 row per loan application (ADR-001)
-- Retired dbt_fabric/models/mart/fact_loan_application.sql (ADR-008).
IF NOT EXISTS (SELECT 1 FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id
               WHERE s.name = 'dbo' AND t.name = 'fact_loan_application')
BEGIN
    CREATE TABLE dbo.fact_loan_application (
        fact_loan_application_sk VARBINARY(32) NOT NULL,  -- HASHBYTES surrogate key (C6), not the grain key
        SK_ID_CURR                  BIGINT     NOT NULL,  -- grain key
        applicant_id                 BIGINT     NOT NULL
    );
END;

CREATE OR ALTER PROCEDURE dbo.usp_build_fact_loan_application
AS
BEGIN
    SET NOCOUNT ON;
    TRUNCATE TABLE dbo.fact_loan_application;
    INSERT INTO dbo.fact_loan_application (fact_loan_application_sk, SK_ID_CURR, applicant_id)
    SELECT
        CONVERT(VARBINARY(32), HASHBYTES('SHA2_256', CONVERT(VARCHAR(20), ISNULL(SK_ID_CURR, -1)))),
        SK_ID_CURR,
        applicant_id
    FROM dbo.stg_application;

    EXEC dbo.usp_assert_fact_loan_application_grain;
END;
