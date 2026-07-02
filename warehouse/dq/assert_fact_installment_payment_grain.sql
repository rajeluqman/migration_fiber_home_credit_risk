-- ADR-008 C8: fact grain uniqueness assert for fact_installment_payment.
-- Grain: SK_ID_PREV + NUM_INSTALMENT_NUMBER — docs/DATA_MODEL.md, LOCKED.
CREATE OR ALTER PROCEDURE dbo.usp_assert_fact_installment_payment_grain
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @dupes INT;
    SELECT @dupes = COUNT(*) FROM (
        SELECT SK_ID_PREV, NUM_INSTALMENT_NUMBER FROM dbo.fact_installment_payment
        GROUP BY SK_ID_PREV, NUM_INSTALMENT_NUMBER HAVING COUNT(*) > 1
    ) AS d;
    IF @dupes > 0
        THROW 51011, 'ADR-008 C8 violation: fact_installment_payment grain (SK_ID_PREV, NUM_INSTALMENT_NUMBER) is not unique.', 1;
END;
