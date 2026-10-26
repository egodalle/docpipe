# ADR 0003 — Models: Vertex embeddings + Gemini Flash

- Status: Accepted
- Date: 2026-10-26
- Deciders: Ed Godalle

## Context

Embeddings and generation must be same-project, billed to GCP, and frozen so eval is comparable. Mixing local Ollama in prod and Vertex in demo would split the index.

## Decision

- **Embeddings:** one Vertex text embedding model, name + dimension frozen in `config.yaml`. Query and chunk use that model only.
- **Generation:** Gemini Flash. Strict RAG prompt; no tools; no agents.
- Local Ollama is **not** used in P1 so the index cannot drift.

Exact model IDs are pinned in week 3 when we first embed (record the ID in config and in this ADR as an amendment note). Until then the placeholder is `text-embedding-004` and `gemini-2.0-flash` (or the current Flash alias).

## Consequences

- **Good:** One IAM surface (Vertex user); cost is small if we cache embeddings by chunk hash.
- **Bad:** Requires Vertex API enabled and a billing account; no fully offline demo.
- **Not chosen:** Mixed local/hosted models; OpenAI; fine-tuning.
