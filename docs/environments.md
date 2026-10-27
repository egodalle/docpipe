# Environments and cost — DocPipe P1

| Field | Value |
| --- | --- |
| Document | DOC-007 |
| Version | 1.1 |
| Date | 2026-10-26 |

## Environments

| Name | Purpose | Database | Objects | Models | Who applies |
| --- | --- | --- | --- | --- | --- |
| `local` | Daily dev | Docker Compose pgvector :5433 | `data/raw/` gitignored | Vertex (same IDs as prod) | Engineer laptop |
| `gcp` | Demo / prod | Cloud SQL Postgres 16 `db-f1-micro` **stopped unless working** | GCS corpus bucket | Vertex | Terraform (`infra/`) |

Region: `us-east1`. BigQuery dataset location: `us-east1`.

## Secrets

| Secret | Where | In git? |
| --- | --- | --- |
| `DATABASE_URL` | Secret Manager + local `.env` | No |
| GCP user ADC | `gcloud auth application-default login` | No |

Commit `.env.example` and `infra/terraform.tfvars.example` only.

## Cost envelope ($25 cap)

| Item | Control |
| --- | --- |
| Cloud SQL `db-f1-micro` | Default **stopped**. ~$0.01/hour only while ALWAYS. Disk still small. |
| Cloud Run | Scale to zero |
| Vertex + Gemini Flash | Cache embeddings; tiny golden set |
| GCS / BigQuery / Dataform | Free-tier volume |
| VPC / private IP / HA | **Do not enable** |

Budget resource in Terraform: amount **$25**, thresholds 50% and 80% email to the operator.

If the $20-equivalent alert fires: stop Cloud SQL first, then pause Vertex calls.

## Naming

| Resource | Name |
| --- | --- |
| GCP project | `docpipe-p1` (ID may get a numeric suffix) |
| GCS bucket | `docpipe-p1-corpus-<project-number>` |
| Cloud SQL instance | `docpipe-pg` |
| Cloud Run job | `docpipe-ingest` |
| Cloud Run service | `docpipe-api` |
| BigQuery dataset | `docpipe_p1` |
| Dataform assertion dataset | `docpipe_p1_assertions` |
| Service accounts | `sa-docpipe-ingest`, `sa-docpipe-api` |
