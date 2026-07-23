-- ADR-008 C4: one-current invariant, BOTH directions, every run. THROWs if any applicant_id has
-- >1 current row OR 0 current rows ("exactly one", not "at most one"). Wired as a Data Factory
-- FAIL branch immediately after either SCD2 build proc (dim_applicant_scd2_merge.sql /
-- dim_applicant_scd2_fallback.sql) — this is also the mandatory backstop C5 relies on if the
-- expire+insert transaction is somehow not atomic in practice.

CREATE OR ALTER PROCEDURE dbo.usp_assert_dim_applicant_one_current
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @too_many INT, @zero_current INT;

    SELECT @too_many = COUNT(*)
    FROM (
        SELECT applicant_id
        FROM dbo.dim_applicant
        WHERE is_current = 1
        GROUP BY applicant_id
        HAVING COUNT(*) > 1
    ) AS over_current;

    IF @too_many > 0
    BEGIN
        THROW 51001, 'ADR-008 C4 violation: >1 is_current=1 row found for one or more applicant_id in dbo.dim_applicant.', 1;
    END;

    SELECT @zero_current = COUNT(*)
    FROM (
        SELECT s.applicant_id
        FROM dbo.int_applicant_attributes AS s
        LEFT JOIN dbo.dim_applicant AS d
            ON d.applicant_id = s.applicant_id AND d.is_current = 1
        WHERE d.applicant_id IS NULL
    ) AS zero_current;

    IF @zero_current > 0
    BEGIN
        THROW 51002, 'ADR-008 C4 violation: 0 is_current=1 rows found for one or more applicant_id present in the source — an SCD2 build left an applicant with no current row.', 1;
    END;
END;
