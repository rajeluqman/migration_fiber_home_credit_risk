-- SCD2 fallback engine (ADR-008 C5 + "Fallback" text) — 2-step UPDATE(expire) + INSERT(new
-- version), NO MERGE statement at all. Swap the Data Factory Gold activity to call this proc
-- instead of dbo.usp_scd2_merge_dim_applicant (dim_applicant_scd2_merge.sql) if Fabric Warehouse
-- MERGE proves immature/unsupported at Gate 1 (unverified until then).
--
-- Same NULL-safe change detection (C3) on the same 4 tracked columns (C2); same HASHBYTES
-- surrogate-key convention (C6). The expire+insert pair MUST be atomic (C5) — a partial failure
-- would leave an applicant with zero current rows, which dbo.usp_assert_dim_applicant_one_current
-- (C4) is the mandatory backstop for, exactly because this fallback exists for the case where
-- Warehouse transaction semantics themselves are the thing under question.

CREATE OR ALTER PROCEDURE dbo.usp_scd2_fallback_dim_applicant
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRANSACTION;

    BEGIN TRY
        -- Step 1: expire current rows that changed (C3 NULL-safe, C2 exact 4 columns).
        UPDATE tgt
        SET end_date   = SYSUTCDATETIME(),
            is_current = 0
        FROM dbo.dim_applicant AS tgt
        INNER JOIN dbo.int_applicant_attributes AS src
            ON src.applicant_id = tgt.applicant_id
        WHERE tgt.is_current = 1
          AND (
                 (src.name_income_type    <> tgt.name_income_type    OR ((src.name_income_type    IS NULL) <> (tgt.name_income_type    IS NULL)))
              OR (src.name_education_type <> tgt.name_education_type OR ((src.name_education_type IS NULL) <> (tgt.name_education_type IS NULL)))
              OR (src.name_family_status  <> tgt.name_family_status  OR ((src.name_family_status  IS NULL) <> (tgt.name_family_status  IS NULL)))
              OR (src.cnt_children        <> tgt.cnt_children        OR ((src.cnt_children        IS NULL) <> (tgt.cnt_children        IS NULL)))
             );

        -- Step 2: insert the new current version for every applicant with zero current rows —
        -- covers brand-new applicants AND the just-expired ones from Step 1 identically.
        INSERT INTO dbo.dim_applicant (
            applicant_sk, applicant_id, SK_ID_CURR, name_income_type, name_education_type,
            name_family_status, cnt_children, start_date, end_date, is_current
        )
        SELECT
            HASHBYTES('SHA2_256',
                CONVERT(NVARCHAR(20), ISNULL(src.applicant_id, -1)) + N'|' +
                CONVERT(NVARCHAR(33), SYSUTCDATETIME(), 126)),
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
