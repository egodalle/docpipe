# Eval baseline — D6

| Field | Value |
| --- | --- |
| Date | 2026-10-27 |
| Corpus | 36 live docs, 188 chunks, 188 embeddings on `:5433` |
| Model | Vertex `text-embedding-004` dim 768 (query embeds only; no Gemini) |
| Golden | [`golden.json`](golden.json) — 28 questions, basename URI match |
| Bar | recall@5 ≥ 0.70 |
| Cloud SQL | not used (STOPPED) |

## One-variable tune

Variable: **unique-document collapse**. Fetch `pool_k` neighbors, keep the first hit per file basename, then cut to k=5. Raw mode is top-5 chunks with no collapse.

| Mode | pool_k | hits / n | recall@5 | Gate |
| --- | --- | --- | --- | --- |
| Raw top-5 chunks | 5 | 27 / 28 | **0.964** | PASS |
| Unique documents | 15 | 28 / 28 | **1.000** | PASS |

**Winner: unique documents** (`eval.unique_documents: true`, `pool_k: 15`). Adopted in `config.yaml` and `/ask`.

The only raw miss was `mvcc` — thin extract, top-5 filled with `README.md`. Unique collapse let `mvcc.html` into the five-document set.

## Commands

```bash
docpipe eval --compare --no-persist
docpipe eval --unique-documents --seed-ingest-run
```
