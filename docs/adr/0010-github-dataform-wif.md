# ADR 0010 — GitHub Actions WIF runs Dataform on merge

- Status: Accepted
- Date: 2026-10-29
- Deciders: Ed Godalle

## Context

v1.0 ran Dataform with `@dataform/cli` from a laptop (ADR 0006). Hosted Dataform Git linking was deferred so we would not put a GitHub PAT in Secret Manager during the sprint. Architecture already named `sa-docpipe-ci` and Workload Identity Federation; RAID R7 cut WIF to hit the v1.0 tag.

A merge to GitHub did not update BigQuery assertion tables. The next step is: push/merge to `main` runs the same warehouse tests in GCP, with no JSON keys.

Hosted Dataform Git remote still compiles from the **repository root**. This repo keeps `dataform.json` under `dataform/` (Python + Terraform + SQLX in one tree). Linking the GCP Dataform UI to GitHub would clone the monorepo and fail to compile.

## Decision

1. **GitHub Actions is the Git → GCP connection.** `npx dataform compile` on pull requests. `npx dataform run` on push to `main` (and `workflow_dispatch`) against BigQuery `docpipe_p1` / `docpipe_p1_assertions`.
2. **Workload Identity Federation**, not a service-account key and not a GitHub PAT. Pool admission is this repository only. The pool impersonates `sa-docpipe-ci`.
3. **`sa-docpipe-ci` may run BigQuery jobs and edit the two P1 datasets.** No Cloud SQL, no GCS write, no Vertex, no Secret Manager.
4. **Do not Git-link a hosted Dataform repository** until Dataform can take a subdirectory. CLI results in BigQuery are the GCP reflection of the merge.

## Consequences

- **Good:** Merge to `main` re-runs warehouse tests in GCP. No keys in GitHub secrets. Cloud SQL stays stopped. Fork PRs cannot impersonate the SA.
- **Bad:** A red Dataform check on `main` means BigQuery is missing seed rows or an assertion failed — fix data or SQLX, do not skip the job. The Dataform console does not show this run (CLI → BigQuery).
- **Not chosen:** GitHub PAT in Secret Manager; hosted Dataform Git SSH (root compile); JSON keys in Actions.
