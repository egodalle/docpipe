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

No application dependencies yet. Ingest and embeddings arrive on later days.

## Postgres (Day 2)

A Homebrew Postgres is already bound to `localhost:5432`, so DocPipe’s Docker instance uses **5433**. Schema `day2` holds practice tables only; the frozen RAG schema is Day 4.

```bash
docker run --name docpipe-pg \
  -e POSTGRES_USER=docpipe \
  -e POSTGRES_PASSWORD=docpipe \
  -e POSTGRES_DB=docpipe \
  -p 5433:5432 \
  -d postgres:16

PGPASSWORD=docpipe psql -h 127.0.0.1 -p 5433 -U docpipe -d docpipe -f sql/seed.sql
PGPASSWORD=docpipe psql -h 127.0.0.1 -p 5433 -U docpipe -d docpipe -f sql/practice.sql
```

SQL primer notes: [notes/day2-sql.md](notes/day2-sql.md). Queries: [sql/practice.sql](sql/practice.sql).
