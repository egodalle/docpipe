# ADR 0007 — Hybrid retrieval with RRF in Postgres

- Status: Accepted
- Date: 2026-10-27
- Deciders: Ed Godalle

## Context

P1 v1.0 retrieved with HNSW cosine only. Unique-document collapse reached recall@5 1.000 on 28 golden questions. Hybrid search (lexical + vector) was cut from the 7-day sprint. Token-exact questions (SQL keywords, function names) still deserve a keyword path without adding Elastic, Vertex AI Search, or a second database.

## Decision

Keep Postgres as the only retrieval system. Add `chunks.body_tsv` (`to_tsvector('english')`, GIN) and fuse **HNSW cosine ranks** with **`ts_rank_cd` ranks** using reciprocal rank fusion (`rrf_k = 60`).

- Default: `retrieval.hybrid: true` in `config.yaml`.
- The citation `score` stays cosine so `refuse_min_score` (0.60) does not change units.
- Unique-document collapse still runs after fusion.
- Compare with `docpipe eval --compare-hybrid`. `--compare` remains the D6 unique-vs-raw experiment on vector-only.

## Consequences

- **Good:** One database; lexical overlap for exact tokens; eval can prove no recall regression; no new billable search service.
- **Bad:** First request after upgrade applies `sql/003_hybrid.sql` (GIN build on 188 chunks is cheap). English stemming only.
- **Not chosen:** Elastic/OpenSearch, Vertex AI Search, a cross-encoder reranker (extra Vertex spend).
