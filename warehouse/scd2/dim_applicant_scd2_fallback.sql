-- SCD2 engine (ADR-008 C5) — 2-step UPDATE(expire) + INSERT(new version), NO MERGE statement.
-- This is now the SOLE SCD2 mechanism (J-021): the MERGE-based proc is retired because Fabric
-- Warehouse does not support the OUTPUT clause on any statement/target, so its
-- MERGE...OUTPUT...INTO @touched design is structurally impossible on this engine — not a
-- maturity gap that this fallback merely hedges against. See @data-architect verdict,
-- migration/governance/GATE3_ARCHITECT_REVIEW_J021.md.
--
-- NULL-safe change detection (C3) on the same 4 tracked columns (C2), rewritten to pure-predicate
-- form (J-021 finding 3 + architect verdict Q2): SQL Server has no boolean type for an IS NULL
-- predicate to evaluate to a value that <> can compare, so the ADR-008-documented compact form
-- `(a<>b) OR ((a IS NULL)<>(b IS NULL))` is invalid T-SQL, not a valid-but-terse restatement (it
-- does not compile on any SQL Server-family engine). The predicate form below —
-- `(a<>b) OR (a IS NULL AND b IS NOT NULL) OR (a IS NOT NULL AND b IS NULL)` — is what
-- warehouse/PROOF_C3_C4_C5.md's own cited dbt-generated SQL actually produces, and is logically
-- total over all 4 {NULL, non-NULL} transition cells (verified live against real Fabric Warehouse
-- compute, J-021). Same HASHBYTES surrogate-key convention (C6), with an explicit
-- CONVERT(VARBINARY(32), ...) outer cast — Fabric Warehouse's HASHBYTES return type is
-- VARBINARY(8000) internally and rejects the implicit truncating conversion into a VARBINARY(32)
-- column (J-021 finding 6). VARCHAR (not NVARCHAR) throughout — Fabric Warehouse's only supported
-- collation (Latin1_General_100_BIN2_UTF8) is UTF-8, under which NVARCHAR is unsupported and
-- VARCHAR stores Unicode losslessly anyway (J-021 finding 2).
--
-- The expire+insert pair MUST be atomic (C5) — a partial failure would leave an applicant with
-- zero current rows, which dbo.usp_assert_dim_applicant_one_current (C4) is the mandatory
-- backstop for, exactly because Warehouse transaction-atomicity across this pair is (unverified)
-- until proven by a forced-failure test (Condition 6, GATE3_ARCHITECT_REVIEW_J021.md).

CREATE OR ALTER PROCEDURE dbo.usp_scd2_fallback_dim_applicant
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRANSACTION;

    BEGIN TRY
        -- Step 1: expire current rows that changed (C3 NULL-safe predicate form, C2 exact 4 columns).
        UPDATE tgt
        SET end_date   = SYSUTCDATETIME(),
            is_current = 0
        FROM dbo.dim_applicant AS tgt
        INNER JOIN dbo.int_applicant_attributes AS src
            ON src.applicant_id = tgt.applicant_id
        WHERE tgt.is_current = 1
          AND (
                 (src.name_income_type    <> tgt.name_income_type    OR (src.name_income_type    IS NULL AND tgt.name_income_type    IS NOT NULL) OR (src.name_income_type    IS NOT NULL AND tgt.name_income_type    IS NULL))
              OR (src.name_education_type <> tgt.name_education_type OR (src.name_education_type IS NULL AND tgt.name_education_type IS NOT NULL) OR (src.name_education_type IS NOT NULL AND tgt.name_education_type IS NULL))
              OR (src.name_family_status  <> tgt.name_family_status  OR (src.name_family_status  IS NULL AND tgt.name_family_status  IS NOT NULL) OR (src.name_family_status  IS NOT NULL AND tgt.name_family_status  IS NULL))
              OR (src.cnt_children        <> tgt.cnt_children        OR (src.cnt_children        IS NULL AND tgt.cnt_children        IS NOT NULL) OR (src.cnt_children        IS NOT NULL AND tgt.cnt_children        IS NULL))
             );

        -- Step 2: insert the new current version for every applicant with zero current rows —
        -- covers brand-new applicants AND the just-expired ones from Step 1 identically.
        INSERT INTO dbo.dim_applicant (
            applicant_sk, applicant_id, SK_ID_CURR, name_income_type, name_education_type,
            name_family_status, cnt_children, start_date, end_date, is_current
        )
        SELECT
            CONVERT(VARBINARY(32), HASHBYTES('SHA2_256',
                CONVERT(VARCHAR(20), ISNULL(src.applicant_id, -1)) + '|' +
                CONVERT(VARCHAR(33), SYSUTCDATETIME(), 126))),
            src.applicant_id, src.SK_ID_CURR, src.name_income_type, src.name_education_type,
            src.name_family_status, src.cnt_children,
            SYSUTCDATETIME(), NULL, 1
        FROM dbo.int_applicant_attributes AS src
        WHERE NOT EXISTS (
            SELECT 1 FROM dbo.dim_applicant d
            WHERE d.applicant_id = src.applicant_id AND d.is_current = 1
        );

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    EXEC dbo.usp_assert_dim_applicant_one_current;
END;
