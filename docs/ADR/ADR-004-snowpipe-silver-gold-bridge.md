# ADR-004: Snowpipe Silver→Gold Bridge — Parent Repo Reference (SUPERSEDED)

> This ADR belongs to the parent repo (`home-credit-pipeline`), where it documents the real,
> hard-won Snowflake `CREATE PIPE` COPY-INTO-only constraint and the resulting downstream dbt
> `QUALIFY ROW_NUMBER()` dedup workaround. It is referenced by this repo's
> `migration/ADR/ADR-005-fabric-full-migration-decision.md` and
> `migration/ADR/ADR-007-validation-parity-protocol.md` as historical context for why Fabric's
> native Delta MERGE is a genuine improvement, not a lateral move.
>
> **The Fabric-repo equivalent is [ADR-004-onelake-merge-idempotency.md](ADR-004-onelake-merge-idempotency.md)**
> — read that instead for this repo's actual idempotency design.
>
> This stub exists only so path references from `migration/ADR/*.md` resolve on disk
> (`tests/doc_reference_contract.py` C2). It is not a decision record for this repo.
