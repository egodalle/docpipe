# Technical design — DocPipe P1

| Field | Value |
| --- | --- |
| Document | DOC-002 |
| Version | 1.0 |
| Status | Approved for execution |
| Date | 2026-10-26 |
| Related | [Charter](CHARTER.md), [Data contract](data-contract.md), [ADRs](adr/README.md) |

## 1. Context

DocPipe turns a GCS prefix of public technical docs into a cited question-answering **data platform**. The customer of the pipeline is a model. The API is a thin contract over retrieval, not a product UI.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Operator    │────▶│ DocPipe (this    │────▶│ Gemini Flash    │
│ (ingest job │     │  repo: jobs+API) │     │ (generation)    │
│  + curl)    │     └────────┬─────────┘     └─────────────────┘
└─────────────┘              │
                             ▼
                    ┌─────────────────┐
                    │ Cloud SQL       │
                    │ documents/      │
                    │ chunks/         │
                    │ embeddings      │
                    └─────────────────┘
```

## 2. Containers

| Container | GCP service | Responsibility |
| --- | --- | --- |
| Object store | GCS `gs://docpipe-p1-corpus` | Source files + `licenses.csv` |
| Ingest | Cloud Run **job** `docpipe-ingest` | Extract, hash, chunk, embed, upsert, quality checks |
| System of record | Cloud SQL Postgres 16 + pgvector | Tables in [data-contract.md](data-contract.md) |
| Serve | Cloud Run **service** `docpipe-api` | `/ask` `/health` `/stats` |
| Embeddings | Vertex AI `text-embedding-004` (dim 768, frozen in `config.yaml`) | Chunk + query vectors, same model both sides |
| Generation | Vertex AI `gemini-3-flash-preview` (global; ADR 0003) | Answer only from retrieved context |
| Analytics | BigQuery `docpipe_p1` | Copies of query_logs, eval_results, ingest_runs |
| Warehouse tests | Dataform CLI (`dataform/`) | Assertions on BQ copies (ADR 0006) |
| Secrets | Secret Manager | DB URL, no other long-lived keys |
| IaC | Terraform (`infra/`) | All GCP resources; Cloud SQL stopped by default |
| Schedule | Cloud Scheduler | Nightly ingest (full incremental). Event-driven is P3. |

## 3. Data flows

**Ingest (batch, incremental)**

1. Job lists GCS objects under `raw/`.
2. For each object: download, extract text (markdown / PDF), SHA-256 content hash.
3. If hash exists in `documents` → skip. If object missing vs last run → tombstone document and cascade chunks/embeddings.
4. Chunk with the default strategy (`recursive_400_80`). Alternate strategy stored but not served until eval says so.
5. Embed new chunks in batches; write `embeddings(model, dim)`.
6. Run data tests; **fail the job** on empty chunks, dim mismatch, duplicate live hashes, orphan embeddings.
7. Write a run row (counts, duration, empty-extract rate) to BigQuery `ingest_runs`.

**Serve**

1. `POST /ask` validates body (question length cap, request id).
2. Embed the question with the **same** embedding model.
3. Hybrid retrieve later is P1 week 5 stretch; v1 default is vector top-k with optional `source` filter, then pack to a token budget.
4. If top score < threshold → HTTP 200 with `refused: true`, no LLM call.
5. Else prompt: answer only from context, cite chunk ids, say you don’t know if missing.
6. Persist `query_logs` (question, chunk ids, scores, answer, latency_ms, model, request_id) in Postgres and ship to BigQuery.

**Eval**

- `eval/golden.json` (28 items: question, expected document URIs).
- Harness scores recall@5 (`docpipe eval`). Unique-document collapse is the default (`eval.unique_documents`, `pool_k=15`).
- Baseline in `eval/baseline.md`: raw 0.964, unique **1.000**. Winner is default config and `/ask`.

## 4. IAM (least privilege)

| Principal | Role |
| --- | --- |
| `sa-docpipe-ingest` | GCS object viewer on corpus; Cloud SQL client; Vertex user; BQ editor on `docpipe_p1` |
| `sa-docpipe-api` | Cloud SQL client; Vertex user; BQ editor on `query_logs` only |
| `sa-docpipe-ci` | WIF from GitHub; run eval job; no corpus write |
| User (Ed) | Owner on the GCP project for Terraform apply |

No JSON keys in the repo. GitHub Actions uses Workload Identity Federation.

## 5. Failure behavior

| Failure | Behavior |
| --- | --- |
| Extract empty / unreadable | Quarantine prefix in GCS `quarantine/`; do not fail the whole job unless empty-extract rate ≥ 5% |
| Embedding API 429 | Retry with backoff; fail the job after N retries |
| Retrieval below threshold | Refuse; do not call Gemini |
| Cloud SQL down | `/health` 503; ingest job fails |
| Prompt injection via docs | Citations still required; no tool use; corpus is public docs only |

## 6. Non-goals in this diagram

Pub/Sub, load balancers, GKE, Vector Search, LangChain agents. See charter §5.

## 7. Local vs GCP

| | Local (dev) | GCP (demo/prod) |
| --- | --- | --- |
| DB | Docker `docpipe-pg` :5433 | Cloud SQL |
| Files | `data/raw/` (gitignored) | GCS |
| Models | Vertex still (no second embedding family) | Vertex |
| Apply | `docker compose` / scripts | Terraform |

Same schemas, same job code, different connection strings.
