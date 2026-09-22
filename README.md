# DocPipe

Postgres + pgvector pipeline that turns a folder of documents into a cited retrieval service.

This is a 30-day AI Data Engineer capstone: ingest, clean, chunk, embed, index, and keep the corpus fresh. The one-page brief is frozen until Day 7.

- Role map: [docs/role-map.md](docs/role-map.md)
- Project brief: [docs/project-brief.md](docs/project-brief.md)

## Frozen stack

Python 3.11 · Postgres + pgvector · pytest · Docker Compose · FastAPI later · one embedding model · one LLM.

Out of scope: Spark, Kafka, Kubernetes, fine-tuning.

## Local setup (Day 1)

Requires Python 3.11+, Git, Docker Desktop, and Cursor.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python --version   # expect Python 3.11.x
```

No application dependencies yet. Postgres, ingest, and embeddings arrive on later days.
