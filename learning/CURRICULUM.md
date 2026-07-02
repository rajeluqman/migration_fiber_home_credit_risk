# Curriculum — Home Credit Risk Pipeline (Fabric rebuild-from-scratch)

> @cikgu's module path. Goal: owner can rebuild every layer of this Fabric pipeline from scratch
> on a `drill/*` branch and defend every resume claim in an interview.
> Mental-model → ETL use-case → production bug → debug → syntax LAST.

## M0 — Orientation (Fabric context)
- What: read `docs/BRD.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md` cold (no code yet).
- Fabric-specific: compare the stack table in `docs/ARCHITECTURE.md` with the parent repo's stack.
  Name what was eliminated and WHY for each layer (cite ADR-006 per service).
- DIY: explain the service mapping back, in your own words, citing ADR-006.

## M1 — Bronze ingestion (Fabric Notebook)
- Concept: idempotent ingestion, PK-null quarantine, `ingestion_ts`/`ingestion_date` metadata.
  Same logic as parent repo's `bronze/ingest_bronze.py` — now inside a Fabric Notebook.
- Fabric-specific: why a Notebook activity inside Data Factory (not a Dataflows Gen2 pipeline)?
  → Cite ADR-006 §1: PII DI-002 SHA-256 sentinel-before-NULL ordering cannot be faithfully
  expressed in a Power Query drag-drop canvas without risking silent misapplication.
- Artifact: `notebooks/nb_bronze_ingest.py` (stub — write the real logic as DIY).
- DIY ticket: `learning/diy/TICKET_bronze_ingest_fabric.md`.

## M2 — Silver: PII masking order (ADR-002 — unchanged rule, Fabric Spark surface)
- Concept: WHY sentinel-null must happen before hashing (ADR-002) — the rule is identical.
  The only change: this code now lives in `notebooks/nb_silver_application.py` instead of
  `glue/glue_silver_application.py`. Fabric Runtime 1.3 = Spark 3.5 (Glue 4.0 = Spark 3.3)
  — same PySpark API surface, same masking code.
- Artifact: `notebooks/nb_silver_application.py` (stub).
- DIY ticket: reproduce the masking function (hint: read `docs/ADR/ADR-002-pii-mask-order.md`, NOT the code).

## M3 — Silver: Fabric Spark mechanics + Delta MERGE idempotency
- Concept: Delta MERGE (`MERGE INTO silver_application ON SK_ID_CURR`) is NATIVE in Fabric Spark.
  This eliminates the parent repo's ADR-004 Snowpipe COPY-INTO-only workaround entirely.
  Why this matters: re-running the notebook is safe without a downstream `QUALIFY ROW_NUMBER()` backstop.
- Artifact: `docs/ADR/ADR-004-onelake-merge-idempotency.md` (read this), then `notebooks/nb_silver_bureau.py`.
- Production bug angle: what if you forget the MERGE and just do an overwrite? Trace the downstream
  dedup failure path.

## M4 — Gold: warehouse/ staging → intermediate → mart (dbt retired, ADR-008)
- Concept: the 3-layer staging/intermediate/mart structure is UNCHANGED, but it's now plain
  T-SQL views + stored procs, no dbt. `QUALIFY` does not exist in T-SQL. How do you rewrite
  `QUALIFY ROW_NUMBER() OVER (...) = 1`?
- Artifact: `warehouse/{staging,intermediate,mart}/` — read the real SQL, then extend it.
- DIY ticket: rewrite `stg_application.sql` for T-SQL without using `QUALIFY` (hint: it already
  is — compare to the retired dbt version in git history, `git log -- dbt_fabric/`).

## M5 — SCD Type 2 (the resume-proof centerpiece — mechanism changed, grain didn't)
- Concept: `dbt snapshot`/`strategy: check` retired → a T-SQL MERGE stored proc
  (`warehouse/scd2/dim_applicant_scd2_merge.sql`) with a NULL-safe per-column comparison
  (ADR-008 C3) doing the same job `dbt_valid_from`/`dbt_valid_to` used to. Run
  `tests/identity_contract.py` to see the static gate.
- Artifact: `warehouse/scd2/dim_applicant_scd2_merge.sql` (+ `_fallback.sql`) and
  `warehouse/mart/dim_applicant.sql`.
- Fabric-specific: why can't a single MERGE statement both expire an old row AND insert its new
  version in one pass? (Answer: same key can't hit two branches — see the comment in
  `dim_applicant_scd2_merge.sql` and `warehouse/PROOF_C3_C4_C5.md`.)

## M6 — Orchestration (Data Factory — replaces Airflow)
- Concept: 3 chained Data Factory pipelines replacing the 3 chained Airflow DAGs.
  Pass/fail branching → Teams connector (not Slack). Data Activator for metric-threshold.
- Artifact: `pipelines/` (stubs) + `docs/PIPELINE_SPEC.md` §5.
- Production bug angle: if nb_silver_bureau fails, does nb_silver_application re-run? Trace the
  pipeline dependency chain (ADR-006 §3 + PIPELINE_SPEC.md §5.2).

## M7 — Quality gates (inline assertions — replaces Great Expectations)
- Concept: WARN-vs-FAIL gate design, now expressed as plain PySpark/Python `assert` statements
  in the notebook's final cell. Why NOT Purview DQ as the gate? (cite ADR-006 §5 verbatim).
- Artifact: `docs/DQD.md` — read the assertion table, then write the assertion cell yourself.

## M8 — Defend the resume (Fabric claims)
- Read `INTERVIEW_GUIDE.md` Fabric claims table.
- Which claims are in-progress vs confirmed? Can you explain why each one is not yet confirmed?
- Drill the Q&A section until you can answer all 4 Fabric-specific questions without notes.
