# ADR 0001 — Vector store: Cloud SQL + pgvector

- Status: Accepted
- Date: 2026-10-26
- Deciders: Ed Godalle

## Context

P1 needs nearest-neighbor search over chunk embeddings plus metadata filters (`source`, live documents only). Options: Vertex AI Vector Search, AlloyDB, Cloud SQL Postgres + pgvector, a hosted specialty store (Pinecone).

## Decision

Use **Cloud SQL for PostgreSQL 16 with pgvector**. Documents, chunks, embeddings, and query logs live in one database. Hybrid search (tsvector + vector) can be added in SQL without a second system.

## Consequences

- **Good:** One backup/IAM story; DE-native (SQL, FKs, unique hashes); matches Google’s Cloud Run + Cloud SQL RAG pattern; cheap to pause.
- **Bad:** ANN at millions of vectors is not this project’s problem; HNSW on a small instance is enough for 20–50 files.
- **Not chosen:** Vertex Vector Search (hides the data path we need to defend in interviews); Pinecone (off-GCP, extra bill).
