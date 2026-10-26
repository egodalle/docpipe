# Environments and cost — DocPipe P1

| Field | Value |
| --- | --- |
| Document | DOC-007 |
| Version | 1.0 |
| Date | 2026-10-26 |

## Environments

| Name | Purpose | Database | Objects | Models | Who applies |
| --- | --- | --- | --- | --- | --- |
| `local` | Daily dev | Docker `docpipe-pg` :5433, db `docpipe` | `data/raw/` gitignored | Vertex (same IDs as prod) | Engineer laptop |
| `gcp` | Demo / prod | Cloud SQL Postgres 16 | GCS `docpipe-p1-corpus` | Vertex | Terraform |

There is no staging environment in P1. Eval runs against `gcp` before tagging `v1.0`, and against `local` during development.

Region: `us-east1`.

## Secrets

| Secret | Where | In git? |
| --- | --- | --- |
| `DATABASE_URL` | Secret Manager + local `.env` | No |
| GCP user ADC | `gcloud auth application-default login` | No |
| GitHub WIF | Workload Identity Federation | No |

Commit `.env.example` only.

## Cost envelope (order of magnitude)

| Item | If left running | How we control it |
| --- | --- | --- |
| Cloud SQL small Postgres | ~$30–70 / month | Stop instance between demos |
| Cloud Run | Near $0 at this traffic | Scale to zero |
| Vertex embeddings | Cents if cached by hash | Never re-embed unchanged chunks |
| Gemini Flash | Cents on golden set + demos | Refusal path skips LLM |
| GCS / BigQuery | Negligible | Tiny corpus |

**Hard cap:** $90 in any calendar month. Budget alert at $50. If the alert fires, destroy Cloud SQL first.

## Naming

| Resource | Name |
| --- | --- |
| GCP project | `docpipe-p1` (actual ID may get a suffix) |
| GCS bucket | `docpipe-p1-corpus-<project-number>` (globally unique) |
| Cloud SQL instance | `docpipe-pg` |
| Cloud Run job | `docpipe-ingest` |
| Cloud Run service | `docpipe-api` |
| BigQuery dataset | `docpipe_p1` |
| Service accounts | `sa-docpipe-ingest`, `sa-docpipe-api`, `sa-docpipe-ci` |
