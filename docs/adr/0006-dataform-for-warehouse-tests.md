# ADR 0006 — Dataform for warehouse tests

- Status: Accepted
- Date: 2026-10-26
- Deciders: Ed Godalle

## Context

P1 already copies `query_logs`, `eval_results`, and ingest run stats to BigQuery so a hiring manager can query quality like a DE, not only via pytest. We need SQL-level tests on those tables. Options: dbt Core, hand-rolled SQL in CI, Dataform (GCP-native).

## Decision

Use **Dataform** (definitions in this repo, run with `@dataform/cli` against BigQuery) for **warehouse assertions**:

- empty-extract rate < 5%
- recall@5 ≥ 0.70 on the latest eval run
- no non-refused answer with zero citations
- a second ingest on an unchanged corpus reports ~0 reprocessed files

**pytest** remains the test of the Python job (extract, schema, hashes, dim). Dataform does not replace pytest.

Terraform creates the BigQuery datasets and IAM. Hosted Dataform Git linking is optional; the CLI is the v1.0 path so we do not need a GitHub PAT in Secret Manager this week.

## Consequences

- **Good:** GCP-native testing story; assertions are SQL a DE can read; cheap (BigQuery free tier at this volume).
- **Bad:** Assertions fail until the Python job has shipped rows. First runs use seed fixtures.
- **Not chosen:** dbt (saved for Project 2 warehouse copilot so the two projects do not clone each other).
