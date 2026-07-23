-- ADR-008 C8: fact grain uniqueness assert, extends the C4 THROW pattern to fact_bureau_credit.
-- Grain: 1 row = 1 bureau credit record per applicant (SK_ID_BUREAU) — docs/DATA_MODEL.md, LOCKED.
CREATE OR ALTER PROCEDURE dbo.usp_assert_fact_bureau_credit_grain
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @dupes INT;
    SELECT @dupes = COUNT(*) FROM (
        SELECT SK_ID_BUREAU FROM dbo.fact_bureau_credit
        GROUP BY SK_ID_BUREAU HAVING COUNT(*) > 1
    ) AS d;
    IF @dupes > 0
        THROW 51010, 'ADR-008 C8 violation: fact_bureau_credit grain (SK_ID_BUREAU) is not unique.', 1;
END;
