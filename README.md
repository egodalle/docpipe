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
unset DATABASE_URL           # if it still points at the Cloud SQL proxy
docker compose up -d
docpipe serve                # 127.0.0.1:8080
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080) for the demo UI. Same `/ask` as curl: cited answer, score, source file, or a refusal when nothing clears 0.60. This is a local overlay, not a product app. Do not make Cloud Run public for it.

The UI **Corpus path** field (or `POST /corpus`) points ingest at another folder. A DocPipe `data/` directory with `licenses.csv` works; so does a flat or nested folder of html / markdown / text. `docpipe sync --corpus /path/to/docs` is the CLI form. Unchanged hashes skip. `/ask` searches only the active path. Disabled on Cloud Run (`K_SERVICE`). Do not upload other corpora to the P1 GCS bucket ([ADR 0009](docs/adr/0009-dynamic-corpus-path.md)).

```bash
curl -s localhost:8080/health
curl -s localhost:8080/stats
curl -s localhost:8080/api
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

## Hybrid retrieval (post-v1.0)

Vector cosine is fused with Postgres full-text (`tsvector` + GIN) via reciprocal rank fusion. Citation **score stays cosine**, so the 0.60 refuse floor does not change meaning. Default: `retrieval.hybrid: true` ([ADR 0007](docs/adr/0007-hybrid-rrf.md)).

`GET /stats` also reports operator numbers: `asks`, `refused`, `refuse_rate`, `latency_p50_ms`, `latency_p95_ms`. Citations include `source` and `license` from `data/licenses.csv`.

```bash
docpipe eval --compare-hybrid --no-persist
docpipe eval --refuse --no-persist
```

Refuse eval scores 8 off-corpus questions (`eval/refuse.json`). Bar: **all must refuse** (Gemini is not called). `/ask` also checks citation integrity: `[chunk_id]` in the answer must be retrieved ids (`query_logs.citation_ok`, [ADR 0008](docs/adr/0008-refuse-eval-citation-integrity.md)).

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

Deployed: `https://docpipe-api-gl6bq73cza-ue.a.run.app` (authenticated; not public). Scales to zero (`min_instances = 0`, `max_instances = 1`). Live `/ask` against Cloud SQL was proven 2026-10-27 (JSONB cited `datatype-json.html` score 0.755), then SQL was set back to NEVER. While stopped, `GET /` is 200 and `/health` is 503. Start SQL only for a demo, then set NEVER again.

Local stranger path (working without Cloud SQL):

```bash
docker compose up -d
docpipe serve
curl -s localhost:8080/ask -H 'content-type: application/json' \
  -d '{"question":"How does JSONB store JSON in PostgreSQL?"}'
```

SQL primer notes: [notes/day2-sql.md](notes/day2-sql.md). Queries: [sql/practice.sql](sql/practice.sql).
