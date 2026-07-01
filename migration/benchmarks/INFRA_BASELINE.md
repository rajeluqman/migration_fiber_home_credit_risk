# Infrastructure Baseline — AWS Glue Pre-Migration Numbers

> Real observed numbers from the parent repo. Source: `INFRA_LIMITS_LOG.md` (all rows),
> plus corroborating figures from `PROJECT_STATUS.md`. These are the compute
> characteristics of the current pipeline that the Fabric Spark notebooks must match or
> improve on. Every number here is a real measurement, not an estimate.

## Glue job performance (real AWS Glue, G.1X×2, Glue 4.0 = Spark 3.3)

| Job | Input rows | Output rows | Wall time | DPU-seconds | Peak JVM heap (driver+executor) | Ceiling | Headroom | Source |
|---|---|---|---|---|---|---|---|---|
| `glue_silver_bureau` | 1,716,428 (bureau) + 27,299,925 (bureau_balance) = 29,016,353 | bureau 1,716,428 + bureau_balance 610,965 | **96s** (1st run) | **192** | n/a (no metrics, 1st run) | 32 GB | unknown | `INFRA_LIMITS_LOG.md` "Glue OOM risk bureau_balance — RESOLVED" |
| `glue_silver_bureau` (re-run, metrics enabled) | same | same | **118s** | **236** | driver **1.183 GB** + executor **1.713 GB** = **≈2.90 GB peak** | 32 GB | **≈91% headroom** | `INFRA_LIMITS_LOG.md` "Glue peak JVM heap — RESOLVED" |
| `glue_silver_installments` | 13,605,401 | 12,861,994 | **90s** | **180** | not measured (metrics-less run) | 32 GB | unknown | `INFRA_LIMITS_LOG.md` "Glue OOM risk installments — RESOLVED" |
| All other 3 Glue jobs | see SILVER_BASELINE | see SILVER_BASELINE | not separately recorded | not recorded | not measured | 32 GB | unknown | `PROJECT_STATUS.md` ~726-744 |

**Key finding for Fabric sizing:** the heaviest Glue job (`glue_silver_bureau`, 29M input
rows) peaked at **≈2.90 GB / 32 GB = 9% of the executor ceiling**. This confirms the
Kimball flat-table architecture (ADR-003) avoids the fan-out OOM mode — each job
processes one flat table at a time, no cross-table joins in Silver. The Fabric Spark
notebooks should have equivalent or better headroom (Fabric Runtime 1.3 runs Spark 3.5
on medium/large Spark pools).

## Glue infra config (pre-migration state)
Source: `PROJECT_STATUS.md` ~726-744 (Glue job creation entry):

| Config | Value |
|---|---|
| Worker type | G.1X (1 DPU = 4 vCPU / 16 GB) |
| Worker count | 2 |
| Glue version | 4.0 (= Spark 3.3, Python 3.10) |
| Delta Lake | `DATALAKE_FORMATS=delta` env var + `delta-spark==2.1.0` pip install (Docker) |
| S3 output path | `s3://home-credit-risk-staging/silver/{table}/ingestion_date={date}/` |
| Scripts location | `s3://home-credit-risk-staging/glue-scripts/` |

## S3 storage usage (observed, pre-migration)
Source: `INFRA_LIMITS_LOG.md` "S3 actual usage" + `PROJECT_STATUS.md` ~684:

| Bucket | Usage | Object count | Notes |
|---|---|---|---|
| `home-credit-risk-dev-1` | **2.6718 GB** | 75 | landing 2.6571 GB (7 raw CSVs) + bronze/silver sample-scale only |
| `home-credit-risk-staging` | **~3.7959 GB** (post-Bronze+Silver full-scale) | ~hundreds | raw 2.6571 + Bronze 0.6895 + Silver (Delta tables, 7 tables) |
| `home-credit-risk-prod` | **0 GB** | 0 | empty, never populated |
| **Account-wide total** | **~6.5 GB** | — | Exceeds 5 GB free-tier ceiling (acknowledged standing override per `INFRA_LIMITS_LOG.md`) |

**Fabric equivalent:** OneLake storage is metered differently (per-GB/month within
Fabric capacity) — the 5 GB AWS free-tier ceiling does not apply. The Fabric cost
baseline for OneLake storage is captured in `COST_BASELINE.md`.

## Glue spend to date (estimate, pre-migration)
Source: `COST_LOG.md` final entries:

| Category | DPU-seconds | DPU-hours (est.) | $ cost (est.) |
|---|---|---|---|
| All Phase-2 Glue runs (5 jobs, full-scale) | 1,017 | 0.2825 | **≈$0.124** |
| CloudWatch metrics re-run of `glue_silver_bureau` | 502 | 0.1394 | **≈$0.061** |
| **Total Glue spend to date** | **1,519** | **0.4219** | **≈$0.186** |

Basis: ~$0.44/DPU-hour (AWS Glue G.1X estimate). These are estimates, not pulled from
the AWS Billing console. They represent the full cost of proving the pipeline on real
AWS Glue at 58.4M-row scale — the pre-migration economics to compare against Fabric CU
cost (`COST_BASELINE.md`).
