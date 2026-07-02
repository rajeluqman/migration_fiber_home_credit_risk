-- SCD2 primary engine (ADR-008, J-003 lock: "A1" = Fabric Warehouse MERGE) for dim_applicant.
-- Replaces dbt_fabric/snapshots/snap_applicant.sql (`strategy: check`, unique_key='applicant_id',
-- retired). Match key stays applicant_id (C6) — never applicant_sk. WHEN MATCHED compares
-- exactly the 4 tracked columns (ADR-008 C2), each with the NULL-safe
-- "(a<>b) OR ((a IS NULL)<>(b IS NULL))" expansion (C3) — this is the literal expansion dbt's own
-- `check` strategy macro generates per column, so behaviour matches dbt on a NULL-transition row.
-- See warehouse/PROOF_C3_C4_C5.md for the worked side-by-side proof.
--
-- A single MERGE can expire an existing current row (WHEN MATCHED) or insert a brand-new
-- applicant (WHEN NOT MATCHED BY TARGET), but it cannot also insert the *new version* of a row
-- it just expired in the same statement (same key can't hit two branches). So: MERGE does the
-- expire + brand-new-insert and OUTPUTs which applicant_ids were touched; one follow-up INSERT
-- adds the new-version row for the ones that were expired (not the brand-new ones, which already
-- got their row from WHEN NOT MATCHED BY TARGET — the WHERE NOT EXISTS guard below tells them
-- apart). Both statements share ONE transaction — C5's atomicity discipline applies here too,
-- not only to the no-MERGE fallback in dim_applicant_scd2_fallback.sql.
--
-- Fabric Warehouse MERGE maturity is (unverified) — confirm against a real workspace at Gate 1.
-- If MERGE misbehaves, point the Data Factory Gold activity at
-- dbo.usp_scd2_fallback_dim_applicant instead (dim_applicant_scd2_fallback.sql).

CREATE OR ALTER PROCEDURE dbo.usp_scd2_merge_dim_applicant
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRANSACTION;

    BEGIN TRY
        DECLARE @touched TABLE (applicant_id BIGINT NOT NULL);

        MERGE dbo.dim_applicant AS tgt
        USING dbo.int_applicant_attributes AS src
            ON tgt.applicant_id = src.applicant_id AND tgt.is_current = 1
        WHEN MATCHED AND (
                 (src.name_income_type    <> tgt.name_income_type    OR ((src.name_income_type    IS NULL) <> (tgt.name_income_type    IS NULL)))
              OR (src.name_education_type <> tgt.name_education_type OR ((src.name_education_type IS NULL) <> (tgt.name_education_type IS NULL)))
              OR (src.name_family_status  <> tgt.name_family_status  OR ((src.name_family_status  IS NULL) <> (tgt.name_family_status  IS NULL)))
              OR (src.cnt_children        <> tgt.cnt_children        OR ((src.cnt_children        IS NULL) <> (tgt.cnt_children        IS NULL)))
             )
        THEN UPDATE SET
            tgt.end_date   = SYSUTCDATETIME(),
            tgt.is_current = 0
        WHEN NOT MATCHED BY TARGET
        THEN INSERT (applicant_sk, applicant_id, SK_ID_CURR, name_income_type, name_education_type,
                     name_family_status, cnt_children, start_date, end_date, is_current)
             VALUES (
                HASHBYTES('SHA2_256',
                    CONVERT(NVARCHAR(20), ISNULL(src.applicant_id, -1)) + N'|' +
                    CONVERT(NVARCHAR(33), SYSUTCDATETIME(), 126)),
                src.applicant_id, src.SK_ID_CURR, src.name_income_type, src.name_education_type,
                src.name_family_status, src.cnt_children,
                SYSUTCDATETIME(), NULL, 1
             )
        OUTPUT ISNULL(deleted.applicant_id, inserted.applicant_id) INTO @touched (applicant_id);

        -- New-version row for every applicant_id the MERGE just expired. Brand-new applicants
        -- already got their row via WHEN NOT MATCHED BY TARGET, so WHERE NOT EXISTS (already
        -- current) tells the two cases apart and never double-inserts.
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
        INNER JOIN @touched AS t ON t.applicant_id = src.applicant_id
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

    -- C4: post-MERGE one-current invariant gate, both directions — Data Factory wires this
    -- proc's failure as its own FAIL branch.
    EXEC dbo.usp_assert_dim_applicant_one_current;
END;
