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

## Fabric Trial capacity — real CU figure (corrects earlier SKU-string assumption)
An earlier session (J-014/J-016/J-017) read the Trial capacity's SKU string via
`fab api -X get capacities/{id}` as `FTL4` and assumed "4" in the SKU name meant "4 CU". That
assumption was **wrong** and is corrected here with a real citation.

| Property | Value | Source |
|---|---|---|
| Fabric Trial capacity | **64 CU** (Capacity Units) | `https://learn.microsoft.com/en-us/fabric/enterprise/licenses#capacity` (accessed 2026-07-03) |
| SKU equivalent | **F64** | same |
| Power BI v-cores | **8** | same |
| `FTL4` SKU string (from `fab api -X get capacities/{id}`) | internal Trial SKU identifier — **not** a CU count; "4" here is unrelated to the CU-table value | (unverified — Microsoft does not publicly document what `FTL4` itself encodes; only the CU-table mapping above is sourced) |

**Important scope note:** 64 CU is a **compute-power** rating (how much aggregate Spark/Warehouse/
Power BI throughput the capacity can sustain), not a documented concurrency or Livy-session-count
limit. Microsoft's public licensing page does not publish an exact "max concurrent Spark sessions"
or "max job submissions per minute" number for Trial capacity. Any concurrency/throttle number
below this line that is *not* cited to the licensing page is derived empirically from real job
submissions in this repo and is labeled **empirical, not official** — it characterizes this one
Trial capacity's observed behavior under real `RunNotebook` load, not a documented SLA.

## Fabric Trial capacity — empirical throttle characterization (RunNotebook, `[TooManyRequestsForCapacity]` HTTP 430)
**(empirical, not official — see scope note above)**

Real `RunNotebook` submissions against `nb_bronze_ingest`
(`d56abc42-a29e-4b1b-8554-737b5e5a7f3d`, workspace `home-credit-risk-dev`), all confirmed via
`GET .../jobs/instances/{id}` polling to a terminal state (not assumed from the `202`):

| # | Session | Job ID | Submitted (UTC) | Gap since prior attempt | Terminal state | Livy-session-creation time | Error |
|---|---|---|---|---|---|---|---|
| 1 | J-016 | `5109f7c9-...` | 2026-07-02 22:19:52 | — (first) | Failed | 1.7s | `[TooManyRequestsForCapacity]` HTTP 430, `isRetriable:false` |
| 2 | J-016 | `01c2051a-...` | 2026-07-02 22:23:47 | ~4 min | Failed | 0.9s | same |
| 3 | J-017 | `56d19605-...` | 2026-07-02 23:29:23 | ~66 min | Failed | 1.4s | same |
| 4 | J-017 | `516f61b6-...` | 2026-07-02 23:35:33 | ~5 min | Failed | 1.0s | same |
| 5 | J-017 | `e4916913-...` | 2026-07-02 23:45:31 | ~8 min (+ ~60s `NotStarted` queue) | Failed | 1.4s (after 60s queue) | same |
| 6 | J-018 | `b0404f35-...` | 2026-07-05 09:06:04 | **~3 days** (cross-session) | Failed | 2.2s | same, `isRetriable:false` |

**Reading of attempt 6 (the material new data point this session):** even a ~3-day gap between
sessions did not clear the throttle — the failure mode, error code, and `isRetriable:false` flag
are byte-for-byte identical to attempts 1-5. This weakens the "just wait longer, minutes-to-hours
scale" hypothesis from J-017 and is consistent with either (a) a sustained/structural Trial-SKU
ceiling rather than a transient burst limit, or (b) some other tenant-wide contention outside this
workspace's visibility (not distinguishable from the Contributor-role SP's vantage point — see
methodology section below). **All 6 attempts across 3 sessions have failed identically; zero
successful `RunNotebook` execution against real Fabric compute to date.**

**New in attempt 6 — response headers captured** (`fab api ... --show_headers`, not available/used
in J-016/J-017): the `202 Accepted` on submission carries `Retry-After: 60` and `x-ms-job-id`
headers. The `Retry-After: 60` value did **not** predict success — attempt 6 still failed with
`[TooManyRequestsForCapacity]` well inside that window (the job failed at Livy-session-creation
2.2s after submission, before the 60s `Retry-After` elapsed). This means `Retry-After` here is
best read as "don't re-submit for at least 60s," not "guaranteed clear after 60s." Also notable:
the job's `status` field lagged in `NotStarted` for a full ~48s of polling (6 polls at 8s
intervals) after the job had *already* reached a `Failed` terminal state internally
(`endTimeUtc` shows failure at T+2.2s) — the status API itself has observed staleness on this
Trial capacity; poll a few extra cycles past what timestamps alone would suggest before trusting
a `NotStarted`/`Running` read as current.

## Methodology — how this baseline was measured (reusable pattern, not Home-Credit-specific)
**What was measured:** end-to-end latency from job submission to terminal state
(`Completed`/`Failed`/`Cancelled`), and failure-mode classification — specifically, whether a
failure happens at **Livy-session-creation stage** (before any Spark executor is allocated, no
notebook code has run) versus an **execution-stage failure** (executor allocated, notebook code
started, then failed). All 6 real attempts to date failed at Livy-session-creation stage, in
0.9-2.2s, which is diagnostic on its own: execution-stage failures on a 27M/13M-row-scale
notebook would take much longer to surface (minutes, not seconds) and would carry a different
error surface (Spark stack trace, not an API-gateway-level `HTTP 430`).

**API surface used** (Fabric REST API v1, via `fab api`, `fab` CLI 1.6.1):
- Submit: `POST workspaces/{workspaceId}/items/{itemId}/jobs/instances?jobType=RunNotebook` →
  `202 Accepted`, `Location` header points at the job instance, `x-ms-job-id` header echoes the
  new job ID, `Retry-After` header present (observed value: `60`, seconds).
- Poll: `GET workspaces/{workspaceId}/items/{itemId}/jobs/instances/{jobInstanceId}` → job
  document with `status` (`NotStarted`/`Running`/`Failed`/`Completed`/`Cancelled`),
  `startTimeUtc`/`endTimeUtc`, and (on failure) a `failureReason` object with `message` and
  `isRetriable` boolean.
- List (audit/reconciliation): `GET workspaces/{workspaceId}/items/{itemId}/jobs/instances`
  returns all historical job instances for that item — used to confirm no submissions were
  silently dropped or double-counted across sessions.
- Cancel: `POST .../jobs/instances/{jobInstanceId}/cancel` exists, but only operates on an
  **active** (not-yet-terminal) job — tried against an already-`Failed` job instance
  (`e4916913-...`) this session and got `400 JobAlreadyCompleted`, confirming the endpoint is
  cancel-only, not resume/replay.
- **No resume/replay endpoint exists.** Probed
  `POST .../jobs/instances/{jobInstanceId}/resume` (a made-up guess at a resume path) → `404
  EntityNotFound`. `fab api --help` and the documented Fabric Jobs REST surface expose exactly
  three job-instance operations: GET (status), POST .../cancel, and creating a brand-new instance
  via `POST .../jobs/instances?jobType=...` on the **item**, not the job-instance ID. Given the
  failure occurs before any Spark executor starts (Livy-session-creation stage — see above),
  there is no partial/checkpointed state to resume from even if such an endpoint existed:
  continuing after a failed attempt always means a fresh `RunNotebook` submission against the
  same item ID, never a special "resume the failed job" call.
- Headers: `fab api <endpoint> --show_headers` surfaces response headers (used for attempt 6);
  prior sessions (attempts 1-5) did not pass this flag and so have no header evidence — this is a
  methodology improvement mid-series, not a re-measurement of the earlier attempts.

**What was NOT measurable in this sandbox, and why:**
- No Capacity Metrics / CU-consumption numbers. `GET admin/capacities/{id}` → `404 NotFound`.
  `GET admin/capacities/{id}/usage` → `404 NotFound`. `GET capacities/{id}/metrics` → `404
  EntityNotFound`. All three probed live this session (not assumed from memory). The workspace's
  service principal holds Contributor role on the workspace only, not a tenant-level Fabric Admin
  role — the Admin Monitoring / Capacity Metrics APIs are gated behind that higher role and are
  not reachable this way. Actual CU draw for these 6 attempts is therefore **unverified** by any
  billing/metrics API; the best available proxy is that all 6 failed before Spark executor
  allocation, so real Spark CU consumed is plausibly at or near zero (not billing-confirmed).
- No concurrent-Spark-session or job-burst quota number is published by Microsoft for Trial
  capacity (see CU scope note above) — so there is no official number to validate the empirical
  throttle against; only Fabric's own runtime error message (`[TooManyRequestsForCapacity]`) is
  available as ground truth.

**Retry cadence used, and its limits:** a fixed/ad-hoc cooldown-and-retry pattern was used, not a
rolling window or exponential backoff: ~4 min → ~66 min → ~5 min → ~8 min (with a ~60s internal
queue delay on attempt 5) → **~3 days** (attempt 6, this session, cross-session gap). **Sample
size is 6 attempts total across 3 sessions — too small to fit a real throttle-recovery curve.**
Be explicit that this does not conclusively separate "Trial SKU has a hard low ceiling regardless
of wait time" from "this specific workspace/tenant has ongoing unrelated contention" — attempt 6's
3-day gap failing identically leans toward the former, but 1 data point at that gap length is not
proof. A rigorous follow-up would need either (a) a longer, unbroken observation window with
attempts spaced on a real exponential schedule (1 min, 2 min, 4 min, ... hours), or (b) a
side-by-side second Trial capacity/workspace as a control — neither was in scope this session.

**How to reuse this pattern in a different project:** (1) identify the job-submission and
job-status-poll endpoints for the target platform's REST API; (2) submit, poll to a real terminal
state (never assume success/failure from the submission response alone); (3) classify failures by
*stage* (pre-execution/gateway-level vs. execution-level) since that distinguishes a
capacity/quota problem from a code/data problem; (4) capture response headers on every attempt,
not just the body — rate-limit signals (`Retry-After`, `x-ms-*` quota headers) usually live there;
(5) vary the gap between attempts across orders of magnitude (minutes → hours → days) rather than
retrying at one fixed interval, and log every attempt's exact gap and outcome in a table like the
one above; (6) explicitly probe for and report on admin/metrics endpoints even if you expect them
to 404 — a documented 404 is stronger evidence than an assumed one; (7) state the sample-size
ceiling honestly rather than fitting a curve to too few points.
