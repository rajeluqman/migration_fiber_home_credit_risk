# Proof: C3 (NULL-safe change detection) / C4 (one-current THROW gate) / C5 (atomic fallback)

> Required by @data-architect's contingent sign-off on `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md`
> (`MIGRATION_JOURNEY.md` J-008/J-009). Originally a static, worked-example proof written before
> any live Fabric Warehouse existed. **Updated 2026-07-06 (J-021):** a real Fabric Trial Warehouse
> now exists and this proof's core claim — the compact NULL-safe form being "logically identical"
> to dbt's generated SQL — turned out to be wrong (the compact form doesn't compile on any SQL
> Server-family engine). See `migration/governance/GATE3_ARCHITECT_REVIEW_J021.md` for the full
> review. This file now documents both the corrected logic and what has actually been run against
> real Fabric Warehouse compute (the `dim_applicant_scd2_merge.sql` proc referenced below is
> retired — see `migration/superseded/`).

## C3 — NULL-safe change detection, side-by-side vs dbt

### The row
`applicant_id = 100001`. Current row in `dim_applicant` (inserted on an earlier run, before the
applicant had reported any children):

| column | value |
|---|---|
| `name_income_type` | `Working` |
| `name_education_type` | `Higher education` |
| `name_family_status` | `Married` |
| `cnt_children` | `NULL` |

Latest source row (`warehouse/intermediate/int_applicant_attributes.sql`) for the same applicant
— they've now reported 2 children:

| column | value |
|---|---|
| `name_income_type` | `Working` |
| `name_education_type` | `Higher education` |
| `name_family_status` | `Married` |
| `cnt_children` | `2` |

Only `cnt_children` changed, and it changed **from NULL**, which is exactly the transition a
naive `<>` comparison gets wrong.

### What a naive comparison does (the bug C3 exists to prevent)
```sql
WHERE src.cnt_children <> tgt.cnt_children   -- NULL <> 2 evaluates to UNKNOWN, not TRUE
```
T-SQL three-valued logic: `NULL <> 2` is `UNKNOWN`, and a `WHERE` clause only keeps rows where
the predicate is `TRUE`. `UNKNOWN` is treated as `FALSE` — so this applicant would be silently
skipped. No new SCD2 version is written, no version boundary is recorded at the point their
child count went from unknown to 2, and the SCD2 history is wrong forever after (a downstream
analyst querying "income type at the time cnt_children was first populated" gets no row).

### What dbt's own `check` strategy actually generates (not a naive `<>`)
dbt's `check` strategy was never a bare `<>` either — its snapshot macro (`snapshot_check_strategy`
→ the row-changed expression in `dbt/include/global_project/macros/materializations/snapshots/`)
expands each tracked column to:
```sql
(
    source_data.cnt_children != snapshotted_data.cnt_children
    or (
        (source_data.cnt_children is null) and not (snapshotted_data.cnt_children is null)
    )
    or (
        (not source_data.cnt_children is null) and (snapshotted_data.cnt_children is null)
    )
)
```
**Correction 2026-07-06 (J-021, `migration/governance/GATE3_ARCHITECT_REVIEW_J021.md`):** this
proof originally claimed the compact form below was "logically identical" to dbt's generated SQL
above:
```
(a <> b) OR ((a IS NULL) <> (b IS NULL))
```
That claim was wrong — this is **invalid T-SQL on any SQL Server-family engine**, not a
valid-but-terse restatement. SQL Server has no boolean type for an `IS NULL` predicate to
evaluate *to a value* that `<>` can compare against another `IS NULL` predicate; confirmed live
against real Fabric Warehouse compute (`SELECT 1 WHERE (('a'<>'b' OR (('a' IS NULL)<>('b' IS
NULL))))` fails with "Incorrect syntax near '<'."). Neither SCD2 proc that used this form
compiled. The actual fix is the **pure-predicate form**, which dbt's own generated SQL quoted
above already uses (`is null ... and not (... is null)` joined by `and`/`or`, never `<>` on
`IS NULL` results):
```
(a <> b) OR (a IS NULL AND b IS NOT NULL) OR (a IS NOT NULL AND b IS NULL)
```
This is logically total over all 4 {NULL, non-NULL}² transition cells (re-derived and verified
live in J-021): NULL→value and value→NULL both correctly evaluate TRUE (changed); value→same-value
and NULL→NULL both correctly evaluate FALSE (unchanged, including the two-unknowns case dbt itself
treats as no-change).

### What `warehouse/scd2/dim_applicant_scd2_fallback.sql` does (sole SCD2 mechanism as of J-021 —
### the MERGE-based proc is retired, archived at `migration/superseded/dim_applicant_scd2_merge.sql`,
### because Fabric Warehouse does not support the `OUTPUT` clause on any statement)
```sql
WHERE tgt.is_current = 1
  AND (
         (src.name_income_type    <> tgt.name_income_type    OR (src.name_income_type    IS NULL AND tgt.name_income_type    IS NOT NULL) OR (src.name_income_type    IS NOT NULL AND tgt.name_income_type    IS NULL))
      OR (src.name_education_type <> tgt.name_education_type OR (src.name_education_type IS NULL AND tgt.name_education_type IS NOT NULL) OR (src.name_education_type IS NOT NULL AND tgt.name_education_type IS NULL))
      OR (src.name_family_status  <> tgt.name_family_status  OR (src.name_family_status  IS NULL AND tgt.name_family_status  IS NOT NULL) OR (src.name_family_status  IS NOT NULL AND tgt.name_family_status  IS NULL))
      OR (src.cnt_children        <> tgt.cnt_children        OR (src.cnt_children        IS NULL AND tgt.cnt_children        IS NOT NULL) OR (src.cnt_children        IS NOT NULL AND tgt.cnt_children        IS NULL))
     )
```
Same per-column predicate-form expansion, same 4 tracked columns (ADR-008 C2). For
`applicant_id = 100001`: the `cnt_children` clause evaluates `TRUE` exactly as it does in dbt's
generated SQL above — the row is expired (`end_date = SYSUTCDATETIME()`, `is_current = 0`) and a
new current version is inserted with `cnt_children = 2`. **Behaviour matches dbt on this
NULL-transition row — proven against real Fabric Warehouse compute in J-021 (scratch-table
end-to-end run), not only on paper.**

## C4 — one-current THROW gate, both directions

`warehouse/dq/assert_dim_applicant_one_current.sql` checks two failure modes, not one:

1. **>1 current** — `GROUP BY applicant_id HAVING COUNT(*) > 1` where `is_current = 1`. This
   catches a bug where the SCD2 proc inserted a new version without first expiring the old one
   (e.g. a dropped `WHEN MATCHED` branch, or the fallback's Step 1 UPDATE silently no-op'ing).
2. **0 current** — every `applicant_id` present in `int_applicant_attributes` must LEFT JOIN to
   at least one `is_current = 1` row in `dim_applicant`; if not, the applicant has zero current
   rows. This catches the C5 failure mode below.

"Exactly one," not "at most one" — a `UNIQUE` constraint on `(applicant_id) WHERE is_current = 1`
would only catch case 1, not case 2. Both directions are load-bearing because fact→dim joins on
`is_current = 1` drop an applicant silently if case 2 occurs (no error, just missing rows in
every downstream KPI) — that failure mode is invisible without an explicit zero-current check.

## C5 — atomic fallback proof

If Step 1 (`UPDATE ... SET is_current = 0`) commits and the process then dies before Step 2
(`INSERT ... new version`) runs, the applicant has **zero current rows** — the exact case 2
above. Wrapping both statements in one `BEGIN TRANSACTION ... COMMIT TRANSACTION` (with
`ROLLBACK` in the `CATCH` block) in `dim_applicant_scd2_fallback.sql` means a mid-transaction
failure rolls back the UPDATE too — the applicant keeps their previous current row
(last-known-good state) rather than being left with none. `usp_assert_dim_applicant_one_current`
(C4) is the mandatory backstop for the case where Fabric Warehouse transaction semantics
themselves prove not to be atomic in practice — **still (unverified) as of J-021**: the
happy-path output has been proven against real Fabric Warehouse compute (scratch-table
end-to-end run), but a mid-transaction forced-failure has not yet been tested to confirm the
`ROLLBACK` genuinely restores the pre-UPDATE state on this engine. See
`migration/governance/GATE3_ARCHITECT_REVIEW_J021.md` Condition 6 — G7 will not be signed until
either this rollback path is proven or reliance on the C4 backstop is explicitly documented as
the accepted mitigation.

## Summary

| Condition | Mechanism | Where |
|---|---|---|
| C2 | Exactly 4 tracked columns, never `SELECT *` | `dim_applicant_scd2_fallback.sql`, sole SCD2 proc as of J-021 |
| C3 | Per-column `(a<>b) OR (a IS NULL AND b IS NOT NULL) OR (a IS NOT NULL AND b IS NULL)`, matches dbt's own generated SQL — pure-predicate form, corrected 2026-07-06 (J-021) | `dim_applicant_scd2_fallback.sql` |
| C4 | THROW on >1 current AND on 0 current | `warehouse/dq/assert_dim_applicant_one_current.sql`, called at the end of the SCD2 proc |
| C5 | Single transaction wraps expire+insert; C4 is the backstop if atomicity itself is ever violated | `dim_applicant_scd2_fallback.sql` |

**Verified 2026-07-06 (J-021) against real Fabric Warehouse compute** (happy-path only — see the
C5 rollback-path caveat above): C2/C3 confirmed via a scratch-table end-to-end run reproducing
this exact `applicant_id = 100001` NULL→2 transition, plus an unrelated unchanged applicant and a
brand-new applicant, in the same run — all three came out correct, and the one-current check
returned zero violations. The original MERGE-based proc never compiled (table variables and the
`OUTPUT` clause are both unsupported on Fabric Warehouse) and is retired
(`migration/superseded/dim_applicant_scd2_merge.sql`). Still **(unverified)**: the C5
mid-transaction rollback path on real data (Condition 6 above), and this same logic against the
full real Silver dataset rather than a scratch fixture.
