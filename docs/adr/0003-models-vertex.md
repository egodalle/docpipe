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

## Amendment 2026-10-26 (D3)

Pinned in `config.yaml` and live Vertex (`docpipe-p1`, `us-east1`):

| Role | ID | Dim |
| --- | --- | --- |
| Embeddings (chunks + queries) | `text-embedding-004` | **768** |
| Generation (unused until D5) | `gemini-2.0-flash` | — |

Live probe returned dim 768, matching `sql/001_init.sql` `vector(768)` / `CHECK (dim = 768)`. No ALTER. Changing the model or dim requires a new amendment and a schema migration.

## Amendment 2026-10-27 (D5)

`gemini-2.0-flash` was shut down 2026-06-01. Live probe on `docpipe-p1`:

| Role | ID | Location |
| --- | --- | --- |
| Embeddings | `text-embedding-004` dim 768 | `us-east1` (unchanged) |
| Generation | **`gemini-3-flash-preview`** | **`global`** |

`us-east1` / `us-central1` publisher 404 for Gemini 2.0/2.5. Charter §7 allows a location ADR when quota/availability forces it. Embeddings stay `us-east1` so the index does not move. Generation uses a separate Gen AI client so `vertexai.init` for embeddings is not overwritten.

## Consequences

- **Good:** One IAM surface (Vertex user); cost is small if we cache embeddings by chunk hash.
- **Bad:** Requires Vertex API enabled and a billing account; no fully offline demo.
- **Not chosen:** Mixed local/hosted models; OpenAI; fine-tuning.
