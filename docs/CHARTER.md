# Project charter — DocPipe GCP (P1 v1.0)

| Field | Value |
| --- | --- |
| Document | DOC-001 |
| Version | 1.1 |
| Status | Approved for execution — **schedule amendment 2026-10-26** |
| Owner | Ed Godalle (engineer, operator, reviewer) |
| Sponsor | Self — portfolio for AI Data Engineer roles |
| Kickoff | 2026-10-26 |
| Target ship | **2026-11-02** (7-day sprint) |
| Capacity | Unlimited hours this week |
| Cost cap | **$25** total for P1 |

## Amendment log

| Date | Change |
| --- | --- |
| 2026-10-26 v1.0 | Kickoff: six-week plan, $90 cost envelope |
| 2026-10-26 v1.1 | 7-day sprint; $25 cap; Dataform warehouse tests; Terraform required |

## 1. Problem

Operational documents (Postgres / pgvector docs in v1) sit in object storage while models guess. Wrong answers come from missing extracts, bad chunks, stale embeddings, and no citations. DocPipe owns ingest → clean → chunk → embed → index → keep-fresh so a model can retrieve grounded passages.

This phase lifts the v0 local prototype onto GCP: **Terraform** is how the environment is created. Cloud SQL, Cloud Run, Vertex, BigQuery, and Dataform assertions are how it is operated and tested.

## 2. Outcome (definition of done)

A stranger can:

1. `terraform apply` into a dedicated GCP project (Cloud SQL starts **stopped**)
2. Load the seed corpus from GCS
3. `curl` `POST /ask` and get an answer **with citations**
4. Read **eval numbers** (recall@5, citation hit rate) in the README
5. Re-run ingest on an unchanged corpus and see **~0 files re-processed**
6. Run **Dataform assertions** against BigQuery copies of ingest/eval tables

No chat UI is required for v1.0.

## 3. Users

| Role | Need |
| --- | --- |
| Internal teammate (primary) | Cited answers over a known corpus, not vibes |
| LLM (downstream) | Retrieved chunks + a strict prompt only |
| Operator (this repo) | Hashes, empty-extract rate, recall@k, incremental no-op |
| Hiring manager (reader) | Architecture, data contract, eval table, Terraform, how to run — in 3 minutes |

## 4. In scope (P1)

- Terraform for GCS, Cloud SQL (pgvector), Cloud Run job + API, Secret Manager, IAM, BigQuery, budget alert
- GCS as source of record for 20–50 public markdown/PDF files (Postgres + pgvector docs)
- Cloud Run **job** for extract → chunk → embed → index
- Cloud SQL Postgres 16 + pgvector (`db-f1-micro`, no HA, stopped when idle)
- Cloud Run **service** for `POST /ask`, `GET /health`, `GET /stats`
- Vertex AI embeddings + Gemini Flash (one model each, frozen in config)
- BigQuery dataset for `query_logs`, `eval_results`, `ingest_runs`
- **Dataform** assertions on those BigQuery tables (warehouse tests)
- pytest on the Python job
- Golden set of 20–30 questions; recall@5 target ≥ 0.70 after one tuning pass

## 5. Out of scope (P1)

- Spark, Kafka, Dataflow, Dataproc, GKE, Kubernetes
- Vertex AI Vector Search, Pinecone, LangChain-as-architecture
- Fine-tuning / training loops
- Streaming freshness via Pub/Sub (**Project 3**)
- Governed text-to-SQL / dbt (**Project 2** — Dataform is the P1 test layer only)
- Streamlit/Gradio as a ship gate
- Shared VPC, PSC, Cloud Armor, custom domains
- Private/employer documents
- Hybrid search (cut from the 7-day sprint)
- Hosted Dataform GitHub PAT linking (CLI is enough)

## 6. Success metrics (gates)

| Gate | Metric | v1.0 bar |
| --- | --- | --- |
| Ingest | Eligible files in `documents` with hash + URI | 100% of seed corpus |
| Quality | Empty-extract rate | < 5% (pytest + Dataform) |
| Freshness | Re-run on unchanged corpus | ~0 files re-processed |
| Retrieval | recall@5 on 20–30 golden questions | ≥ 0.70 |
| Product | Citations; refuse below score threshold | Required |
| Ship | `terraform apply` + curl from a clean checkout | Required |
| Warehouse tests | Dataform assertions pass on latest BQ load | Required |
| Cost | P1 spend | ≤ **$25** |

## 7. Constraints

- GCP only. Region: `us-east1` unless quota forces a change (ADR if so).
- Python 3.11. One embedding model, one LLM, frozen in config.
- Cloud SQL is **stopped by default** in Terraform (`activation_policy = NEVER`). Start only while working or demoing.
- Public IP + Cloud SQL Auth Proxy. No VPC connector (cost).
- No application secrets in git. `.env.example` only.
- Local Docker Postgres on port 5433 remains the **dev** database.

## 8. Dependencies

- GCP billing account (present) and a dedicated project (`docpipe-p1`)
- Vertex AI API quota in `us-east1`
- GitHub repo `egodalle/docpipe`
- Seed corpus licenses recorded before upload to GCS

## 9. Amendment rule

Stack changes need an ADR. Metric or schedule slips go in `docs/raid.md`. Do not reopen sources, tables, or the “no Spark / no UI” list.
