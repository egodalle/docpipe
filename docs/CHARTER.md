# Project charter — DocPipe GCP (P1 v1.0)

| Field | Value |
| --- | --- |
| Document | DOC-001 |
| Version | 1.0 |
| Status | Approved for execution |
| Owner | Ed Godalle (engineer, operator, reviewer) |
| Sponsor | Self — portfolio for AI Data Engineer roles |
| Kickoff | 2026-10-26 |
| Target ship | 2026-12-06 (end of week 6) |
| Capacity | 10–12 hours / week (~70 hours) |

## 1. Problem

Operational documents (Postgres / pgvector docs in v1) sit in object storage while models guess. Wrong answers come from missing extracts, bad chunks, stale embeddings, and no citations. DocPipe owns ingest → clean → chunk → embed → index → keep-fresh so a model can retrieve grounded passages.

This phase lifts the v0 local prototype (repo + Docker Postgres + practice SQL) onto GCP so the system looks like something a team could run: Terraform, IAM, Cloud Run, Cloud SQL, Vertex, eval numbers.

## 2. Outcome (definition of done)

A stranger can:

1. `terraform apply` into a dedicated GCP project
2. Load the seed corpus from GCS
3. `curl` `POST /ask` and get an answer **with citations**
4. Read **before/after eval numbers** (recall@5, citation hit rate) in the README
5. Re-run ingest on an unchanged corpus and see **~0 files re-processed**

No chat UI is required for v1.0.

## 3. Users

| Role | Need |
| --- | --- |
| Internal teammate (primary) | Cited answers over a known corpus, not vibes |
| LLM (downstream) | Retrieved chunks + a strict prompt only |
| Operator (this repo) | Hashes, empty-extract rate, recall@k, incremental no-op |
| Hiring manager (reader) | Architecture, data contract, eval table, how to run — in 3 minutes |

## 4. In scope (P1)

- GCS as source of record for 20–50 public markdown/PDF files (Postgres + pgvector docs)
- Cloud Run **job** for extract → chunk → embed → index
- Cloud SQL Postgres 16 + pgvector
- Cloud Run **service** for `POST /ask`, `GET /health`, `GET /stats`
- Vertex AI embeddings + Gemini Flash (one model each, frozen in config)
- BigQuery dataset for `query_logs` and `eval_results` (analytics copy; Postgres remains system of record)
- Secret Manager, least-privilege service accounts, GitHub Actions (pytest + a cheap eval subset)
- Terraform for all of the above
- Golden set of 20–30 questions; recall@5 target ≥ 0.70 after one tuning pass

## 5. Out of scope (P1)

Recorded so they are not “discovered” in week 5:

- Spark, Kafka, Dataflow, Dataproc, GKE, Kubernetes
- Vertex AI Vector Search, Pinecone, LangChain-as-architecture
- Fine-tuning / training loops
- Streaming freshness via Pub/Sub (that is **Project 3**)
- Governed text-to-SQL (that is **Project 2**)
- Streamlit/Gradio beyond a optional thin page — not a gate
- Shared VPC, PSC, Cloud Armor, custom domains
- Private/employer documents

## 6. Success metrics (gates)

| Gate | Metric | v1.0 bar |
| --- | --- | --- |
| Ingest | Eligible files in `documents` with hash + URI | 100% of seed corpus |
| Quality | Empty-extract rate | < 5% |
| Freshness | Re-run on unchanged corpus | ~0 files re-processed |
| Retrieval | recall@5 on 20–30 golden questions | ≥ 0.70 |
| Product | Citations; refuse below score threshold | Required |
| Ship | Terraform + curl from a clean checkout | Required |
| Cost | Month with Cloud SQL running for demos | ≤ $90 |

## 7. Constraints

- GCP only. Region: `us-east1` unless quota forces a change (ADR if so).
- Python 3.11. One embedding model, one LLM, frozen in config.
- Cloud SQL is stopped or destroyed when not demoing.
- No application secrets in git. `.env.example` only.
- Local Docker Postgres on port 5433 remains the **dev** database; GCP is **demo/prod**.

## 8. Dependencies

- GCP billing account and a dedicated project (`docpipe-p1`)
- Vertex AI API quota in `us-east1`
- GitHub repo `egodalle/docpipe` (exists, private — public at ship)
- Seed corpus licenses recorded before upload to GCS

## 9. Amendment rule

This charter is frozen for the six weeks except for metric slips or a blocked GCP API. Changes go in `docs/raid.md` and, if the stack changes, a new ADR. Do not reopen sources, tables, or the “no Spark / no UI” list.
