# ADR-013: Slack Incoming Webhook for Pipeline-Failure Alerting — Owner override of the Teams decision and the FB4 Slack ban

**Status:** **Accepted 2026-07-06** — Owner decision, overriding a @scope-guardian VETO (recorded
below). Supersedes the Teams-alerting choice in `ADR-006` (Alerting row) and `ADR-009` (steps 3/4/6)
and lifts the FB4 Slack ban in `tests/boundary_contract.py` + `migration/governance/boundary_contract_fabric.py`.
**Date:** 2026-07-06
**Owner:** Raja Ahmad Luqman (single-dev).

## Context
Gate 4 condition **G9** (`migration/governance/SIGN_OFF.md`) required a failure alert to fire on a
simulated pipeline failure. The original design (ADR-006, ADR-009) specified **Microsoft Teams** as
the alerting channel (native to the "Fabric-only, zero third-party" target). During the Gate 4 build
(`MIGRATION_JOURNEY.md` J-023) Teams was proven **genuinely unusable in this tenant**, not merely
unconfigured — three independent dead ends, all confirmed live:

1. Classic Teams **Connectors** (Incoming Webhook) — retired product-wide by Microsoft, unavailable
   in any tenant.
2. The modern **Workflows** app (Teams' Power-Automate-based replacement) — not present/installed in
   this tenant at all, even with the Owner confirmed as Global Administrator.
3. Building the flow directly in the **Power Automate portal** — the Teams connector's OAuth
   connection creation failed with `Failed to create OAuth connection: ... 'First Party Azure Active
   Directory'. Microsoft Accounts are not allowed by their BAP administrator.`

**Root cause:** this Fabric trial tenant is MSA/personal-signup-rooted (created via a personal Gmail
address during Fabric trial signup, not a paid M365 org tenant). Power Platform (BAP) blocks OAuth
for first-party Microsoft services — Teams included — on MSA-rooted tenants as a hard platform
policy, not a Global-Admin-toggleable setting. On top of that, a working Teams automation path would
require a **paid M365 licence** this portfolio project will not fund. Teams is therefore off the
table for the lifetime of this tenant.

## Decision
Use a **Slack Incoming Webhook** (a plain HTTPS `POST` to a `https://hooks.slack.com/services/...`
URL) for pipeline-failure alerting. It is wired as a **Data Factory Web activity on the failure
branch** of the Gold pipeline (`gold_warehouse`), posting a JSON message to a Slack channel. The
webhook URL lives in `.env` as `SLACK_WEBHOOK_URL` (never committed — `.gitignore` covers `.env`).

No `slack_sdk` / `slackclient` Python dependency is introduced — the alert is a raw webhook `POST`,
so nothing imports a Slack SDK. The FB4 ban is nonetheless **lifted** (see Governance) so the repo's
own contract stops asserting a falsehood ("no Slack anywhere") now that Slack is a sanctioned part
of the alerting path.

## Governance — this reverses a hard boundary, recorded honestly
FB4 (`no AWS/Snowflake/Airflow/Slack reintroduced`) exists because Slack was part of the retired
parent-repo (AWS/Snowflake) stack; re-admitting it is a partial, deliberate walk-back of the
migration's "retire the old stack" scope. This was **not** waved through:

- **@scope-guardian VETOED it** (2026-07-06, full review in `MIGRATION_JOURNEY.md` J-024). Verdict:
  `VETO on Slack — no carve-out, no ADR amendment, no exception.` Reasoning: unlike FB7 (which
  ADR-009 authorised as a *logically necessary* exception — a suspended capacity cannot resume
  itself), notification-on-failure is a *substitute-rich* problem, so no necessity justifies a
  banned-SDK carve-out. Recommended alternatives instead: **Azure Monitor Action Group → email**
  (OAuth-free, ARM-native) or an **SMTP-based Logic App** (sidesteps the first-party-AAD/BAP block
  that killed Teams), either folded into the already-approved ADR-009 Logic App.
- **The Owner overrode the veto** (2026-07-06), with explicit reasoning: (a) declined to add any new
  Azure service (Action Group / Logic App SMTP would grow the external footprint beyond the single
  capacity-lifecycle Logic App already carved out under FB7); (b) Teams requires paid licensing this
  project won't fund; (c) a Slack Incoming Webhook is the lowest-footprint path that needs no new
  Azure resource and no first-party-AAD OAuth. Per this repo's own governance rule, the **Owner
  holds final authority on stack/scope decisions** — @scope-guardian's veto is advisory to the
  Owner, and the Owner has exercised that authority here.

This ADR is the honest record of that override. @scope-guardian's veto stands as reviewed and is
**not** rescinded or rewritten — it was overruled by the one authority that can overrule it.

## What changes
- `tests/boundary_contract.py` + `migration/governance/boundary_contract_fabric.py`: FB4 no longer
  bans `slack_sdk`/`slackclient`. FB1 (AWS), FB2 (Snowflake), FB3 (Airflow) are **unaffected** — they
  remain hard bans; only Slack is re-admitted, and only for alerting.
- FB7's sub-clause "remains subject to the FB1–FB4 bans (no AWS/Snowflake/Airflow/Slack)" narrows to
  "FB1–FB3 bans (no AWS/Snowflake/Airflow)".
- ADR-006 Alerting row and ADR-009 steps 3/4/6 change "Teams" → "Slack (ADR-013)".
- `.env.example`: `TEAMS_WEBHOOK_URL` → `SLACK_WEBHOOK_URL`.
- G9 evidence becomes a **Slack message screenshot** rather than a Teams message log.

## What this is NOT
Not a reopening of FB1/FB2/FB3 — AWS, Snowflake, and Airflow stay banned. Not a general re-adoption
of Slack for anything beyond pipeline-failure alerting. Not a precedent that any FB1–FB4 ban is
negotiable on request — this required an explicit, recorded Owner override of a standing veto, which
is the highest-friction path in this repo's governance, precisely so it cannot happen silently.

## Consequences
**(+)** G9 becomes achievable in this tenant with zero new Azure resources and no paid licence.
**(+)** The repo's contract stops asserting a falsehood about its own stack.
**(−)** The "zero third-party alerting" property of the Fabric-native target is given up; Slack (a
  non-Microsoft SaaS) is now in the alerting path. Owner accepts this as a pragmatic
  portfolio-project trade-off given the tenant constraints.
**(−)** A standing @scope-guardian veto was overridden — recorded transparently here so the
  governance trail stays truthful.

## Sign-off
- [ ] **@scope-guardian** — **VETO (2026-07-06)**, overridden by Owner (see Governance above). Not
  rescinded; overruled.
- [x] **Owner** — decision 2026-07-06: "aku mmg finalize nak guna slack. teams ni mmg kena bayar.
  apa2 docs adr or gate etc ubah ke slack." Final authority exercised.
