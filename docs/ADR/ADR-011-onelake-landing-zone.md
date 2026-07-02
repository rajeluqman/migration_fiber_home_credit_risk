# ADR-011: Explicit OneLake Landing Zone Ahead of Bronze

**Status:** **Proposed** — pending Owner GO (Gate 2-adjacent; does not block Silver logic dev).
**Date:** 2026-07-02
**Owner:** Raja Ahmad Luqman (single-dev).

## Context
The pipeline as designed through ADR-006 §2 ingests **Kaggle API → Fabric Notebook → OneLake
Bronze (Delta)** directly (`docs/PIPELINE_SPEC.md` "Bronze Layer", `docs/ARCHITECTURE.md` Data
Flow). Bronze therefore does **two jobs at once**: it is the *landing point* for the raw
download AND the *first curated Delta layer* (CSV parsed into typed columns, `ingestion_ts`/
`source_file`/`batch_id`/`env` metadata attached, partitioned by `ingestion_date`).

Conflating those two jobs is a common medallion simplification ("Bronze = raw"). It works, but it
throws away the raw ingress as an independent, immutable artifact: once the CSV is parsed into a
Bronze Delta table, schema-on-write has already been applied, and the byte-for-byte original is
gone unless the source is re-fetched.

Fabric makes the separation cheap and natural. A single OneLake Lakehouse exposes **two areas**:
- **Files** — unmanaged, arbitrary files (raw CSV, checksums), the OneLake equivalent of a raw
  landing bucket.
- **Tables** — managed Delta tables (Bronze/Silver/Gold).

So a landing zone is `home_credit_lakehouse/Files/landing/` and Bronze is
`home_credit_lakehouse/Tables/bronze_*`. **Same Lakehouse item, same workspace, same billing,
zero cross-cloud egress** — this is a refinement *within* ADR-006 §2's "one storage surface"
principle, not a new storage system and not a new Fabric service.

## Decision
Introduce an **explicit Landing layer** between the Kaggle download and Bronze:

```
Kaggle API → Fabric Notebook → Landing (raw CSV, as-is)      → Bronze (Delta, typed, +metadata) → Silver → Gold
                                home_credit_lakehouse/Files/    home_credit_lakehouse/Tables/
                                landing/<batch_id>/<file>.csv   bronze_<table>
```

- **Landing** stores each downloaded CSV **byte-for-byte as received**, under a batch-scoped path
  (`Files/landing/<batch_id>/<file>.csv`) plus a recorded SHA-256 checksum and the original
  filename. Landing is **append-only and immutable** — never edited, never masked, never typed.
- **Bronze** is materialized **from Landing** (not from the Kaggle API): parse CSV → typed Delta
  table, attach `ingestion_ts`/`source_file`/`batch_id`/`env`, partition by `ingestion_date`.
  Bronze remains exactly as specified in `docs/PIPELINE_SPEC.md` — its **input source changes
  from "the Kaggle API response" to "the Landing file"**, nothing else.
- The Kaggle API is hit **once per ingestion**, at the Landing step only. Bronze re-materialization
  never re-calls Kaggle.

## Why a separate Landing zone beats Bronze-as-landing
1. **Raw immutability / forensic original.** Bronze-as-Delta imposes schema-on-write immediately
   (CSV parsed, types inferred). If parsing is wrong (encoding, delimiter, an upstream column
   change), and Bronze is the only copy, the raw original is unrecoverable without re-fetching.
   Landing keeps the exact bytes + checksum, always re-parseable.
2. **Replay without re-hitting the source.** When Bronze logic changes (new metadata column,
   corrected cast, different partitioning), Bronze is rebuilt from Landing — no Kaggle API call,
   which is rate-limited, may change, or may be withdrawn (competition data). This decouples
   *ingestion-from-source* from *Bronze-materialization*.
3. **Provenance / audit — material in a credit-risk (banking) domain.** Landing is the immutable
   "file X arrived at time Y with checksum Z" record; Bronze is already a transformation.
   Separating them makes "what landed" provable independently of "what was materialized."
4. **Schema-drift detection.** With Landing, an incoming raw schema can be diffed against expected
   **before** it reaches (and potentially corrupts) the Bronze Delta write.

## Consequences
**(+)** Raw ingress becomes an independent, auditable, replayable artifact — standard enterprise
  lakehouse practice, and (given this repo's portfolio purpose) an articulable design decision
  rather than an implicit conflation.
**(+)** Bronze reprocessing no longer depends on Kaggle availability.
**(+)** No boundary/scope impact: OneLake **Files** in the *same* Lakehouse — no new service, no
  new connector, no new billing, consistent with ADR-006 §2 and the FB1–FB8 bans.
**(−)** ~2× storage for the raw footprint (raw CSV in Files + Bronze Delta in Tables). In OneLake
  Files this is cheap, but it is real — logged for @finops-agent; retention/compaction of old
  Landing batches is a follow-up hygiene item, not a blocker.
**(−)** One extra pipeline step (Landing → Bronze) in the `bronze_ingestion` Data Factory pipeline.
**(−)** For this specific project the "replay from source" benefit is partly theoretical — the
  Kaggle competition dataset is **frozen**, so the source will not drift. The immutability/audit
  and portfolio-articulation benefits stand regardless; the replay benefit is the weakest for
  this static dataset and is accepted as such.

## Scope — what this ADR does and does NOT change
- **Does NOT touch grain / SCD2 / identity** (ADR-001/008 unchanged) — this is an *ingress-layer*
  decision, upstream of any modelling. `dim_applicant` keying on `SK_ID_CURR` is untouched.
- **Does NOT reopen the stack** — Landing is OneLake Files in the existing Lakehouse; no new
  Fabric service, no new connector, no relaxation of FB1–FB8.
- **Does NOT change Silver/Gold** — Silver still reads Bronze; Gold still reads Silver.
- **Refines ADR-006 §2** — "one storage surface" still holds; Landing is the Files area of the
  same OneLake Lakehouse, not a separate store. ADR-006 §2 is amended by reference, not reversed.

## Alternatives Rejected
- **Keep Bronze-as-landing (status quo).** Rejected — loses raw immutability and forces a Kaggle
  re-fetch for any Bronze logic change; the conflation is the exact thing this ADR removes.
- **Separate Lakehouse item for Landing.** Rejected as unnecessary — a distinct Lakehouse gives
  marginally cleaner separation but adds a second item to manage for no billing or egress benefit;
  the Files/Tables split within one Lakehouse already provides managed/unmanaged separation.
- **Land raw into an external store (e.g. ADLS/S3) first.** Rejected — reintroduces a non-OneLake
  storage surface and cross-cloud egress, violating ADR-006 §2 and the FB1 AWS ban.
