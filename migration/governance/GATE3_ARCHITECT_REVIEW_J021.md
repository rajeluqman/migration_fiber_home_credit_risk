# Gate 3 — @data-architect verdict on the J-021 Fabric Warehouse dialect/logic fix

> Scope: review-only. This file is the written verdict the @senior-data-engineer applies to
> `warehouse/mart/*.sql` and `warehouse/scd2/*.sql`. No `warehouse/` file was touched producing it.
> Evidence discipline: every claim about current code carries `file:line`; every claim I could not
> verify against a real run is tagged `(unverified)`.
>
> Inputs read this turn: `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md`,
> `warehouse/PROOF_C3_C4_C5.md`, `warehouse/mart/dim_applicant.sql`,
> `warehouse/mart/fact_{bureau_credit,installment_payment,loan_application}.sql`,
> `warehouse/scd2/dim_applicant_scd2_merge.sql`, `warehouse/scd2/dim_applicant_scd2_fallback.sql`,
> `warehouse/dq/assert_dim_applicant_one_current.sql`, `docs/DATA_MODEL.md`,
> `MIGRATION_JOURNEY.md` J-021 (lines 845-956).

---

## Q1 — Type-fix set (VARBINARY / VARCHAR / DATETIME2(6) / explicit CONVERT) vs ADR-008 C6

**C6 requires** (ADR-008:66-70): deterministic + collision-safe HASHBYTES surrogate key; explicit
`CONVERT(...)` with fixed style codes for non-string inputs; NULL→sentinel before hashing; and the
surrogate key MUST NOT be the SCD2 match key (identity stays `applicant_id`).

**What the fix changes** and whether C6 survives, per input to the hash — the fix touches the
*encoding* and *output cast* of the hash, never the *value* or the *logic*:

- `BINARY(32)` → `VARBINARY(32)` on the 4 surrogate columns
  (`warehouse/mart/dim_applicant.sql:12`, `fact_bureau_credit.sql:7`,
  `fact_installment_payment.sql:7`, `fact_loan_application.sql:7`). This is a storage-type fix
  only; SHA2_256 output is 32 bytes either way. **C6 collision-safety unaffected** — the hash
  algorithm is unchanged.
- Explicit `CONVERT(VARBINARY(32), HASHBYTES('SHA2_256', ...))` at every insert site. HASHBYTES
  returns `VARBINARY(8000)` in Fabric's engine (J-021 finding 6); the explicit cast is *mandatory*
  and is fully consistent with C6's "pin explicit `CONVERT(...)`" discipline. **Approved — this is
  C6-compliant, not a deviation from it.**
- `NVARCHAR(n)` → `VARCHAR(n)` on the hash inputs and the tracked columns
  (`dim_applicant.sql:15-17` NVARCHAR(64); the `CONVERT(NVARCHAR(20)/(33), ...)` casts inside the
  hashes at `fact_bureau_credit.sql:20`, `fact_installment_payment.sql:24-25`,
  `fact_loan_application.sql:20`, `dim_applicant_scd2_fallback.sql:43-44`). The fixed style code
  `126` on the datetime cast (`..._fallback.sql:44`) is preserved by the fix — **C6's "fixed style
  codes for non-string inputs" holds.** `ISNULL(src.applicant_id, -1)` (`..._fallback.sql:43`) is
  preserved — **C6's NULL→sentinel-before-hashing holds.**

**On VARCHAR replacing NVARCHAR — no objection, and the concern is weaker than it looks.** The only
Fabric Warehouse collation is `Latin1_General_100_BIN2_UTF8`, which is a **UTF-8** collation:
`VARCHAR` under it is UTF-8 encoded and *can* store Unicode. So `NVARCHAR`→`VARCHAR` here is not a
representational-capacity loss at all — it is an encoding change (UTF-16→UTF-8), not a
"drop Unicode support" change. The 4 tracked columns are the Home Credit categorical strings
`name_income_type / name_education_type / name_family_status` (English enum values —
`Working`, `Higher education`, `Married`, etc.) and `cnt_children` (INT); the PII-masked columns
that flow through Silver (`DAYS_EMPLOYED_MASKED`, `DAYS_BIRTH_MASKED`) are SHA-256 hex digests,
i.e. ASCII (`MIGRATION_JOURNEY.md` J-020:788-793). `docs/DATA_MODEL.md:33-42` names the tracked set
but does not enumerate the domain values; I have **not** run a full domain scan, so "no Unicode in
these columns" is **(unverified)** against the live data — but it does not need to be, because
VARCHAR-under-UTF8 stores Unicode losslessly regardless. The swap is safe either way.

**One consistency requirement (see Condition 1).** `SHA2_256(VARCHAR-UTF8 bytes)` differs from
`SHA2_256(NVARCHAR-UTF16 bytes)` for the same logical string. This is harmless here **only because
(a)** no Gold hash is persisted yet — J-021:899-900 confirms "zero of the 4 mart tables" exist, so
there is no pre-existing digest to match and no re-key/backfill hazard — **and (b)** the change is
applied uniformly at every surviving hash site. If it is applied to some sites and not others, two
rows keyed on the same logical value would hash differently. That is the collision/consistency risk
to guard, and it is closed by uniform application, not by anything data-dependent.

**`DATETIME2(7)` → `DATETIME2(6)`** on `start_date`/`end_date` (`dim_applicant.sql:19-20`): a
precision cap, not a grain or identity change. `SYSUTCDATETIME()` still returns precision-7 as a
value; the hash input `CONVERT(VARCHAR(33), SYSUTCDATETIME(), 126)` is unaffected (it converts the
function result, not the column), and 33 chars still holds the ISO-8601 string. No objection.

**Q1 verdict: the type-fix set preserves C6 in full, contingent on Condition 1 (uniform
application). The surrogate key stays derived from `applicant_id`/grain keys, never becomes the
match key — C6's identity clause is intact (`dim_applicant.sql:13`, match key `applicant_id`).**

---

## Q2 — C3 predicate-form rewrite vs ADR-008 C2 and C3

**The current on-disk compact form is invalid T-SQL — this finding is correct and load-bearing.**
Both SCD2 procs carry, per tracked column, `... OR ((a IS NULL) <> (b IS NULL))`
(`dim_applicant_scd2_merge.sql:36-39`, `dim_applicant_scd2_fallback.sql:29-32`). SQL Server has no
boolean type for an `IS NULL` predicate to evaluate *to a value* that `<>` can compare; J-021:918-930
bisected this to a minimal repro that fails identically off-Fabric. **Neither SCD2 proc compiled**
(J-021:925). This also means `warehouse/PROOF_C3_C4_C5.md:62-65` overstated equivalence: it claimed
the compact form is "logically identical" to dbt's generated SQL, but the compact form is
syntactically invalid, not a different-but-equivalent expression. The proof's *own cited* dbt SQL
(`PROOF_C3_C4_C5.md:51-60`) already uses the pure-predicate form
(`... is null and not (... is null)` joined by `and`/`or`), never `<>` on `IS NULL` results.

**The proposed rewrite** —
`(a <> b) OR (a IS NULL AND b IS NOT NULL) OR (a IS NOT NULL AND b IS NULL)` — is logically identical
to dbt's generated SQL (`PROOF_C3_C4_C5.md:51-60`) and is valid T-SQL. I re-derived all three edge
cases (src = new/source, tgt = old/snapshot):
- **NULL→'2'** (tgt=NULL, src='2'): `src<>tgt`=UNKNOWN(false); `src IS NULL AND tgt IS NOT NULL`=false;
  `src IS NOT NULL AND tgt IS NULL`=**TRUE** → CHANGED. Correct (this is the exact bug C3 exists to
  catch — `PROOF_C3_C4_C5.md:37-45`).
- **'x'→'x'**: all three disjuncts false → SAME. Correct.
- **NULL→NULL**: `NULL<>NULL`=UNKNOWN(false); both null-branches false → SAME. Correct (two unknowns
  are not a version cut — matches dbt).

The rewrite is **symmetric** (covers both NULL→value and value→NULL), so it is correct in both
transition directions, not just the one worked in the proof. **No logical gap beyond the 3 tested
cases** — the predicate is total over the {NULL, non-NULL}² space, and I checked all four cells.

**C2 (exactly 4 tracked columns, never `SELECT *`):** the rewrite changes only the *per-column
expression form*, not the column *set*. The set stays `name_income_type, name_education_type,
name_family_status, cnt_children` (`dim_applicant_scd2_fallback.sql:29-32`, matching
`ADR-008:52` and `DATA_MODEL.md:39-42`). **C2 satisfied — unchanged.**

**Q2 verdict: the predicate-form rewrite satisfies C2 and C3 as claimed, and is not a new
decision — it is the correction of ADR-008's own invalid "compact form" restatement (ADR-008:57)
back to the predicate form the proof already cited. See Condition 5 (the ADR/proof text must be
corrected, since the compact form as written is wrong, not merely terse).**

---

## Q3 — Abandon MERGE proc, promote the 2-step fallback to sole/primary SCD2 mechanism

**Consistent with ADR-008's own contingency language — no new ADR, no re-grain.** ADR-008 specified
the fallback as a first-class, pre-authorised path from the start:
- Decision (ADR-008:36-38): "→ a T-SQL SCD2 `MERGE` stored proc. **Fallback: a 2-step
  `UPDATE`(expire) + `INSERT`(new version) if Fabric Warehouse `MERGE` proves immature** (maturity
  **unverified** — confirm against real Fabric before build)."
- Consequences (ADR-008:117): "Fabric Warehouse `MERGE` maturity is unverified — **the 2-step
  fallback exists for this.**"
- C5 (ADR-008:62-65) is written *specifically about the fallback's* atomicity — it is not an
  afterthought, it is a binding condition on the exact path now being promoted.

J-021 finding 5 (OUTPUT unsupported on any statement/target, `MIGRATION_JOURNEY.md` task brief +
J-021:913-917 for the table-variable half) is precisely "MERGE proves immature" — the primary proc's
whole design (`MERGE ... OUTPUT ... INTO @touched` then a keyed follow-up INSERT,
`dim_applicant_scd2_merge.sql:30,55,60-76`) is structurally impossible on Fabric Warehouse, not
patchable. Exercising the pre-authorised fallback is the same move ADR-008 itself made when it
exercised ADR-006 §4 "Option B" (ADR-008:6-7). **Grain, identity, tracked-column set, and the
one-current invariant are all unchanged — this is a mechanism swap inside the envelope ADR-008
already drew, not a re-grain.** No new ADR is required.

**But it does require a documentation amendment (C1 discipline), because two governing docs go
false the moment the primary MERGE proc is retired:**
- `DATA_MODEL.md:36-37` names `dbo.usp_scd2_merge_dim_applicant` as *the* mechanism with the
  fallback secondary — this sentence becomes false.
- `ADR-008:36-38` and `:117` still frame MERGE as primary and the 2-step as contingent.
Per C1 (ADR-008:48-50, "the doc that goes false the moment X must be amended in the same PR"), these
must be updated in the same PR that lands the code fix, each citing J-021 finding 5. This is an
**amendment** (cite-the-ADR-it-amends), not a new ADR. See Conditions 2, 3, 4.

**C5 (atomic fallback, single transaction, C4 backstop) on the promoted fallback:** the fallback
proc already satisfies C5's structure — expire (`UPDATE`, `..._fallback.sql:21-33`) + insert
(`..._fallback.sql:37-52`) are wrapped in one `BEGIN TRANSACTION ... COMMIT` with `ROLLBACK` in the
`CATCH` (`..._fallback.sql:17,54,56-58`), and it `EXEC`s the C4 gate at the end
(`..._fallback.sql:61`). It uses **no** table variable and **no** OUTPUT, so J-021 findings 4/5 do
not touch it (this is why it "worked end-to-end on first try" in the scratch test). Once the type
fixes + C3 rewrite + explicit CONVERT land, its C5 structure is intact.

**Caveat on C5 — the atomicity *rollback path* is still (unverified).** The scratch test proved the
fallback's **happy-path output** (correct rows on success). It did **not** prove that a
mid-transaction failure actually rolls back the Step-1 `UPDATE` on Fabric Warehouse — i.e. that
`BEGIN TRAN/ROLLBACK` is genuinely atomic across the expire+insert pair on this engine. C5 itself
anticipated exactly this ("If Fabric Warehouse transaction semantics across the pair are unverified,
C4's zero-current check is the mandatory backstop and blocks the run", ADR-008:64-65;
`PROOF_C3_C4_C5.md:108-112`). See Condition 6 — this is the one place I will not let G7 be signed on
happy-path evidence alone.

**Q3 verdict: promotion is within ADR-008's contingency envelope (no new ADR); the fallback's C5
structure is preserved; conditional on the doc amendments and the rollback-path/one-current proof.**

---

## Q4 — Anything else I block on before this ports back into `warehouse/`

The type-fix set + C3 rewrite + fallback promotion are directionally **approved**. I attach the
following conditions; all are applied by @senior-data-engineer, not me.

### Blocking conditions
1. **Apply every hash-site change uniformly.** The *surviving* hash sites after the merge proc is
   retired are exactly 4: `dim_applicant_scd2_fallback.sql:42-44`, `fact_bureau_credit.sql:20`,
   `fact_installment_payment.sql:23-25`, `fact_loan_application.sql:20`. Each must get **both**
   `NVARCHAR→VARCHAR` on its inputs **and** the outer `CONVERT(VARBINARY(32), HASHBYTES(...))`.
   All 4 `CREATE TABLE` surrogate columns (`dim_applicant.sql:12`, `fact_bureau_credit.sql:7`,
   `fact_installment_payment.sql:7`, `fact_loan_application.sql:7`) go `BINARY(32)→VARBINARY(32)`;
   `dim_applicant.sql:15-17` NVARCHAR(64)→VARCHAR(64); `dim_applicant.sql:19-20`
   DATETIME2(7)→DATETIME2(6). Partial application reintroduces the C6 collision/consistency hazard.
2. **Repoint the wrapper.** `dim_applicant.sql:32` (`usp_build_dim_applicant`) currently `EXEC`s
   `dbo.usp_scd2_merge_dim_applicant`. With the MERGE proc retired, this wrapper must `EXEC`
   `dbo.usp_scd2_fallback_dim_applicant`, or the entire Gold build calls a non-existent/non-compiling
   proc. (This is a `warehouse/mart/` edit — cite this verdict + J-021 finding 5.)
3. **Retire the MERGE proc, don't orphan it.** `warehouse/scd2/dim_applicant_scd2_merge.sql` must be
   deleted or archived under `migration/` labelled "superseded — OUTPUT unsupported on Fabric
   Warehouse, J-021". Leaving a non-compiling, OUTPUT-based proc on disk still labelled "primary"
   (`..._merge.sql:1`, `dim_applicant.sql:3`) is a trap for the next reader and violates the same
   "no half-alive alternative" hygiene ADR-008's scope conditions applied to `dbt_fabric/`
   (ADR-008:83-84).
4. **Same-PR doc amendments (C1).** Amend, each citing J-021: `DATA_MODEL.md:36-37` (name
   `usp_scd2_fallback_dim_applicant` as the primary/sole mechanism); `ADR-008:36-38` and `:117`
   (record that OUTPUT-unsupported — not merely MERGE-immature — triggered the pre-authorised
   fallback promotion). Amendment, not a new ADR — grain/identity/tracked-cols unchanged.
5. **Correct the invalid "compact form" in the ADR and the proof.** `ADR-008:57` states the C3
   compact form `((a<>b) OR ((a IS NULL) <> (b IS NULL)))` and `warehouse/PROOF_C3_C4_C5.md:62-65,
   119` repeat it as "logically identical" to dbt. That form is **invalid T-SQL** (J-021 finding 3),
   not a valid-but-terse restatement. Both must be corrected to the predicate form
   `(a <> b) OR (a IS NULL AND b IS NOT NULL) OR (a IS NOT NULL AND b IS NULL)` — which is what dbt's
   cited SQL (`PROOF_C3_C4_C5.md:51-60`) actually generates. This corrects the record; it does not
   change the C2/C3 *intent*, which was always the predicate form.
6. **Prove the one-current invariant on real data before G7 — do not sign G7 on happy-path output
   alone.** Either (a) force a mid-transaction failure in the promoted fallback against real Fabric
   Warehouse and confirm the Step-1 `UPDATE` rolls back (no applicant left with zero current rows),
   **or** (b) explicitly document reliance on the C4 zero-current `THROW` gate
   (`assert_dim_applicant_one_current.sql:28-40`) wired as a Data Factory FAIL branch as the
   mandatory C5 backstop, per ADR-008:64-65. Additionally, run the exact NULL-transition row the
   proof demands (`applicant_id = 100001`, `cnt_children` NULL→2, `PROOF_C3_C4_C5.md:13-33,124-126`)
   through the promoted fallback on real Warehouse and confirm exactly one current row results —
   this closes the proof's own "(unverified until Gate 1)" line and is the evidence G7 needs.

### Non-blocking notes (for the record, not veto triggers)
- **C7 unaffected** (ADR-008:71-74): no hash in the fixed code takes a raw PII value — the surviving
  hashes key on `applicant_id`/`SK_ID_BUREAU`/`SK_ID_PREV`+`NUM_INSTALMENT_NUMBER`
  (`..._fallback.sql:43`, `fact_bureau_credit.sql:20`, `fact_installment_payment.sql:24-25`,
  `fact_loan_application.sql:20`). Gold does no PII hashing; the fix introduces none.
- **C4/C8 assertion procs are unaffected** by all 6 findings — `assert_dim_applicant_one_current.sql`
  is pure INT counting (no BINARY/NVARCHAR/table-var/OUTPUT), and J-021:896-899 confirms the 3 fact
  grain-assertion procs compiled clean against the real Warehouse. No change needed there.
- **No persisted-hash / re-key hazard**: J-021:899-900 confirms zero mart tables exist yet, so the
  encoding change has nothing to backfill against.

---

## Sign-off

```
[@data-architect — mood: rigorous]

VERDICT: APPROVE-CONDITIONAL

Approved in principle:
  - Type-fix set (BINARY→VARBINARY(32), NVARCHAR→VARCHAR, DATETIME2(7)→DATETIME2(6),
    explicit CONVERT(VARBINARY(32), HASHBYTES(...))) — preserves ADR-008 C6.  (Q1)
  - C3 predicate-form rewrite — satisfies C2 (still exactly 4 tracked cols) and C3
    (NULL-safe, matches dbt's cited SQL, correct on all 4 NULL/non-NULL cells).  (Q2)
  - Retiring the OUTPUT/table-variable MERGE proc and promoting the 2-step fallback to
    sole SCD2 mechanism — within ADR-008's own contingency envelope; NO new ADR, NO re-grain,
    grain/identity/tracked-cols/one-current invariant all unchanged.  (Q3)

Conditions (all BLOCKING; applied by @senior-data-engineer, cite this verdict + J-021):
  1. Apply every hash-site + column-type change UNIFORMLY across the 4 surviving hash sites
     and 4 CREATE TABLEs (partial application = C6 collision hazard).
  2. Repoint usp_build_dim_applicant (dim_applicant.sql:32) to the fallback proc.
  3. Delete/archive dim_applicant_scd2_merge.sql (superseded — don't orphan a non-compiling proc).
  4. Same-PR C1 doc amendments: DATA_MODEL.md:36-37 + ADR-008:36-38/:117 (amendment, not new ADR).
  5. Correct the invalid "compact form" in ADR-008:57 + PROOF_C3_C4_C5.md:62-65,119 to predicate form.
  6. Before G7: prove the one-current invariant on real Fabric Warehouse — rollback-path OR the
     documented C4 backstop, PLUS the applicant_id=100001 NULL->2 transition run.

This does NOT reach my veto: no mixed-grain dimension, no re-grain, no new fact/dim/FK, no
tracked-column-set change, no identity change. The star schema (ADR-001) and the SCD2 grain
(1 row per applicant version, DATA_MODEL.md:18,33) are untouched by this fix.

G6/G7 stay ☐ Pending until Conditions 1-6 land and the real-Warehouse SCD2 run is evidenced.
```
