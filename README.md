# DocPipe

Postgres + pgvector pipeline that turns a folder of documents into a cited retrieval service.

**P1 v1.0:** GCP via **Terraform**, cited `/ask`, eval numbers, **Dataform** assertions. Cost cap **$25**. Cloud SQL stays **stopped** unless you are working.

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

Each `/ask` is stored in Postgres `query_logs` and copied to BigQuery `docpipe_p1.query_logs`.

## Eval (D6)

28 golden questions in [`eval/golden.json`](eval/golden.json). Hit if the expected file basename is in the top 5. Bar: **recall@5 ≥ 0.70**.

One-variable tune — unique-document collapse vs raw top-5 chunks:

| Mode | recall@5 |
| --- | --- |
| Raw top-5 chunks | 0.964 (27/28) |
| Unique documents (winner) | **1.000 (28/28)** |

Winner is the default: `eval.unique_documents: true`, `pool_k: 15` in `config.yaml`. `/ask` uses the same collapse. Baseline: [`eval/baseline.md`](eval/baseline.md).

```bash
docpipe eval --compare --no-persist
docpipe eval                 # persist winner rows to Postgres + BigQuery
cd dataform && npx dataform run
```

## Cloud Run API (D7)

Same image serves `/ask` and `docpipe sync`. Cloud SQL stays **stopped** until you flip `cloud_sql_activation_policy = "ALWAYS"`. Do not leave ALWAYS on overnight.

```bash
# linux/amd64 even on Apple silicon
IMAGE=us-east1-docker.pkg.dev/docpipe-p1/docpipe/api:v1.0.1
docker build --platform linux/amd64 -t "$IMAGE" .
gcloud auth configure-docker us-east1-docker.pkg.dev --quiet
docker push "$IMAGE"
```

Set `api_image` in `infra/terraform.tfvars` to that IMAGE, then:

```bash
cd infra
terraform plan
terraform apply
```

Deployed: `https://docpipe-api-gl6bq73cza-ue.a.run.app` (authenticated; not public). Scales to zero (`min_instances = 0`, `max_instances = 1`). While Cloud SQL is NEVER, `GET /` is 200 and `/health` is 503. Start SQL only for a live `/ask` demo, then set NEVER again.

Local stranger path (working without Cloud SQL):

```bash
docker compose up -d
docpipe serve
curl -s localhost:8080/ask -H 'content-type: application/json' \
  -d '{"question":"How does JSONB store JSON in PostgreSQL?"}'
```

SQL primer notes: [notes/day2-sql.md](notes/day2-sql.md). Queries: [sql/practice.sql](sql/practice.sql).
