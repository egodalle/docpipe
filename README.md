# DocPipe

Postgres + pgvector pipeline that turns a folder of documents into a cited retrieval service.

**P1 (in flight, 7-day sprint):** GCP via **Terraform**, cited `/ask`, eval numbers, **Dataform** assertions. Ship **2026-11-02**. Cost cap **$25**.

- [Project docs](docs/README.md)
- [Charter](docs/CHARTER.md) — executing scope
- [Delivery plan](docs/delivery-plan.md) · [Timeline](docs/timeline.md) · [Status](docs/status.md)
- [Architecture](docs/architecture.md) · [Data contract](docs/data-contract.md)

## Frozen stack (P1)

Python 3.11 · **Terraform** (`infra/`) · GCS · Cloud SQL Postgres 16 + pgvector · Cloud Run (job + API) · Vertex embeddings + Gemini Flash · BigQuery logs · **Dataform** warehouse tests (`dataform/`) · pytest · Secret Manager.

Out of scope: Spark, Kafka, Dataflow, GKE, fine-tuning, a product UI. Cost cap $25 — Cloud SQL stays stopped unless you are working.

## Local setup (Day 1)

Requires Python 3.11+, Git, Docker Desktop, and Cursor.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python --version   # expect Python 3.11.x
```

```bash
pip install -e ".[dev]"
```

## Local Postgres + ingest (D2)

Homebrew already binds `localhost:5432`, so DocPipe’s Docker instance uses **5433**. Practice SQL lives in schema `day2`; P1 rows are `public.documents`.

```bash
docker compose up -d
pip install -e ".[dev]"
docpipe fetch              # 36 licensed files → data/raw (gitignored)
docpipe ingest             # extract, SHA-256, load documents
docpipe upload-gcs         # copy data/raw + licenses.csv to GCS
pytest
```

`data/licenses.csv` is the redistributable manifest (PostgreSQL / MIT). Empty extracts go to `data/quarantine/` and fail the job if the rate is ≥ 5%. Cloud SQL stays **stopped**.

## Local chunk + embed (D3)

Frozen model: Vertex `text-embedding-004`, dim **768** (`config.yaml`, ADR 0003). Same IDs locally and on GCP. Cloud SQL stays **stopped**; embeddings write to Docker `:5433`.

```bash
docpipe index              # chunk recursive_400_80 + batch embed + HNSW
docpipe index              # second run skips known content hashes
docpipe search --examples  # five k-NN queries, logged without an LLM answer
docpipe search "What is JSONB?"
pytest
```

`docpipe chunk` and `docpipe embed` exist if you need the steps split. Skip re-embed when a live `content_hash` already has chunks + embeddings.

## Incremental sync (D4)

Edit one file and only that document is re-chunked/re-embedded. Missing files are tombstoned (chunks dropped).

```bash
docpipe sync               # ingest insert/update/tombstone + index
pytest
```

Cloud Run job `docpipe-ingest` is in Terraform (`infra/run.tf`) but not created until `ingest_image` is set. Do not run it while Cloud SQL is stopped.

## Local API (D5)

Cited `/ask` against Docker `:5433`. Gemini is called only when the top score is ≥ `serve.refuse_min_score` (0.60). Cloud SQL stays **stopped**.

```bash
docpipe serve                # 127.0.0.1:8080
curl -s localhost:8080/health
curl -s localhost:8080/stats
curl -s localhost:8080/ask -H 'content-type: application/json' \
  -d '{"question":"How does JSONB store JSON in PostgreSQL?"}'
curl -s localhost:8080/ask -H 'content-type: application/json' \
  -d '{"question":"What is the weather in Paris tomorrow?"}'
curl -s localhost:8080/ask -H 'content-type: application/json' \
  -d '{"question":"How do I bake sourdough bread at home?"}'
pytest
```

Each `/ask` is stored in Postgres `query_logs` and copied to BigQuery `docpipe_p1.query_logs`. Cloud Run **service** is D7.

SQL primer notes: [notes/day2-sql.md](notes/day2-sql.md). Queries: [sql/practice.sql](sql/practice.sql).
