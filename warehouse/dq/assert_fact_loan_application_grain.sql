-- ADR-008 C8: fact grain uniqueness assert for fact_loan_application.
-- Grain: SK_ID_CURR — docs/DATA_MODEL.md, LOCKED.
CREATE OR ALTER PROCEDURE dbo.usp_assert_fact_loan_application_grain
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @dupes INT;
    SELECT @dupes = COUNT(*) FROM (
        SELECT SK_ID_CURR FROM dbo.fact_loan_application
        GROUP BY SK_ID_CURR HAVING COUNT(*) > 1
    ) AS d;
    IF @dupes > 0
        THROW 51012, 'ADR-008 C8 violation: fact_loan_application grain (SK_ID_CURR) is not unique.', 1;
END;
