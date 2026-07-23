-- grain: SK_ID_PREV + NUM_INSTALMENT_NUMBER — 1 row per installment payment (ADR-001)
-- Retired dbt_fabric/models/mart/fact_installment_payment.sql (ADR-008).
IF NOT EXISTS (SELECT 1 FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id
               WHERE s.name = 'dbo' AND t.name = 'fact_installment_payment')
BEGIN
    CREATE TABLE dbo.fact_installment_payment (
        fact_installment_payment_sk VARBINARY(32) NOT NULL,  -- HASHBYTES surrogate key (C6), not the grain key
        SK_ID_PREV                    BIGINT     NOT NULL,  -- composite grain: SK_ID_PREV + NUM_INSTALMENT_NUMBER
        NUM_INSTALMENT_NUMBER          INT        NOT NULL,  -- see SK_ID_PREV above for the composite grain
        SK_ID_CURR                     BIGINT     NOT NULL
    );
END;

CREATE OR ALTER PROCEDURE dbo.usp_build_fact_installment_payment
AS
BEGIN
    SET NOCOUNT ON;
    TRUNCATE TABLE dbo.fact_installment_payment;
    INSERT INTO dbo.fact_installment_payment (
        fact_installment_payment_sk, SK_ID_PREV, NUM_INSTALMENT_NUMBER, SK_ID_CURR
    )
    SELECT
        CONVERT(VARBINARY(32), HASHBYTES('SHA2_256',
            CONVERT(VARCHAR(20), ISNULL(SK_ID_PREV, -1)) + '|' +
            CONVERT(VARCHAR(20), ISNULL(NUM_INSTALMENT_NUMBER, -1)))),
        SK_ID_PREV,
        NUM_INSTALMENT_NUMBER,
        SK_ID_CURR
    FROM silver.silver_installments;

    EXEC dbo.usp_assert_fact_installment_payment_grain;
END;
