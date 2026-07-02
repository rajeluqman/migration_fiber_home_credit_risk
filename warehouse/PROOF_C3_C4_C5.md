# Proof: C3 (NULL-safe change detection) / C4 (one-current THROW gate) / C5 (atomic fallback)

> Required by @data-architect's contingent sign-off on `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md`
> (`MIGRATION_JOURNEY.md` J-008/J-009). Static, worked-example proof — no live Fabric Warehouse
> exists yet (Gate 1 unsigned), so this cannot be a query-execution screenshot. It is a
> line-by-line logical proof that `warehouse/scd2/dim_applicant_scd2_merge.sql` /
> `dim_applicant_scd2_fallback.sql` reproduce dbt's own `check`-strategy behaviour on a
> NULL-transition row, and that the C4/C5 failure modes they guard against are real. **This
> proof itself is (unverified) against real Fabric Warehouse execution — Gate 1.**

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
which is logically identical to the compact form ADR-008 C3 names:
```
(a <> b) OR ((a IS NULL) <> (b IS NULL))
```
Both forms evaluate this row's `cnt_children` comparison to **TRUE**: `a IS NULL` is `TRUE`,
`b IS NULL` is `FALSE`, so `(a IS NULL) <> (b IS NULL)` is `TRUE` — the OR short-circuits to
`TRUE` regardless of what `a <> b` evaluates to. The row is correctly flagged as changed.

### What `warehouse/scd2/dim_applicant_scd2_merge.sql` does
```sql
WHEN MATCHED AND (
     (src.name_income_type    <> tgt.name_income_type    OR ((src.name_income_type    IS NULL) <> (tgt.name_income_type    IS NULL)))
  OR (src.name_education_type <> tgt.name_education_type OR ((src.name_education_type IS NULL) <> (tgt.name_education_type IS NULL)))
  OR (src.name_family_status  <> tgt.name_family_status  OR ((src.name_family_status  IS NULL) <> (tgt.name_family_status  IS NULL)))
  OR (src.cnt_children        <> tgt.cnt_children        OR ((src.cnt_children        IS NULL) <> (tgt.cnt_children        IS NULL)))
)
```
Same per-column expansion, same 4 tracked columns (ADR-008 C2), applied identically in the
2-step fallback (`dim_applicant_scd2_fallback.sql`). For `applicant_id = 100001`: the
`cnt_children` clause evaluates `TRUE` exactly as it does in dbt's generated SQL above — the row
is expired (`end_date = SYSUTCDATETIME()`, `is_current = 0`) and a new current version is
inserted with `cnt_children = 2`. **Behaviour matches dbt on this NULL-transition row.**

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
`ROLLBACK` in the `CATCH` block) in both `dim_applicant_scd2_merge.sql` and
`dim_applicant_scd2_fallback.sql` means a mid-transaction failure rolls back the UPDATE too — the
applicant keeps their previous current row (last-known-good state) rather than being left with
none. `usp_assert_dim_applicant_one_current` (C4) is the mandatory backstop for the case where
Fabric Warehouse transaction semantics themselves prove not to be atomic in practice
(unverified — Gate 1): if that ever happens, the zero-current check fails loudly instead of
silently dropping applicants from downstream joins.

## Summary

| Condition | Mechanism | Where |
|---|---|---|
| C2 | Exactly 4 tracked columns, never `SELECT *` | both SCD2 procs, `WHEN MATCHED` / `UPDATE ... WHERE` clauses |
| C3 | Per-column `(a<>b) OR ((a IS NULL)<>(b IS NULL))`, matches dbt's own generated SQL | both SCD2 procs |
| C4 | THROW on >1 current AND on 0 current | `warehouse/dq/assert_dim_applicant_one_current.sql`, called at the end of both SCD2 procs |
| C5 | Single transaction wraps expire+insert; C4 is the backstop if atomicity itself is ever violated | both SCD2 procs |

**(unverified until Gate 1):** all of the above is proven by static SQL-logic inspection, not a
live Fabric Warehouse run. Confirm by executing both procs against a seeded `dim_applicant` +
`int_applicant_attributes` fixture with the exact NULL-transition row above once a real
workspace exists.
