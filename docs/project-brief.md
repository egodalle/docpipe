# DocPipe — project brief

**Status:** Frozen on Day 1. Do not reopen for debate until Day 7.

DocPipe is a document intelligence pipeline: a folder of files becomes a cited question-answering service over Postgres + pgvector, with incremental refresh and an evaluation harness. The job is the data path, not a chatbot demo.

## Problem

Unstructured docs (runbooks, manuals, papers) sit in folders while models guess. Wrong answers come from missing extracts, bad chunks, stale embeddings, and no citations — not from a missing chat UI. DocPipe owns ingest → clean → chunk → embed → index → keep-fresh so a model can retrieve grounded passages.

## Users

- **Primary user:** an internal teammate asking operational questions over a known document set and expecting cited passages, not vibes.
- **Downstream consumer:** an LLM that only sees retrieved chunks plus a strict prompt. If retrieval is wrong, the answer is wrong.
- **Operator (this repo):** the AI Data Engineer who measures empty extracts, duplicate hashes, recall@k, and whether a re-run no-ops an unchanged corpus.

## Sources

Corpus is collected on Day 5. Frozen now:

- **Domain:** PostgreSQL and pgvector documentation (public, redistributable).
- **Size:** 20–50 markdown or PDF files. Tiny on purpose.
- **License:** recorded per file in the repo when collected. No private or employer documents in v1.
- **Change pattern:** files will be edited and removed during the month to prove incremental sync.

No Spark, Kafka, or extra source systems. One local folder is the source of record.

## Success metrics

Ship is not “an answer appeared.” Ship is numbers.

| Gate | Metric | Day-30 bar |
| --- | --- | --- |
| Ingest | Eligible files in `documents` with hash + source URI | 100% of the seed corpus |
| Quality | Empty-extract rate | < 5% |
| Freshness | Re-run on unchanged corpus | ~0 files re-processed |
| Retrieval | recall@5 on 20–30 golden questions | ≥ 0.70 after Day 20 tuning |
| Product | Answers cite sources; refuse below a score threshold | Required behavior, not optional |
| Ship | `docker compose up` from a clean checkout starts db + API | Required |

Baseline eval is Day 19. One-variable experiments are Day 20. Those numbers go in the README; they are not a slide.

## Frozen stack (until Day 7)

Python 3.11 · Postgres + pgvector · pytest · Docker Compose · FastAPI (Day 18) · one embedding model · one LLM (Ollama local or a cheap hosted model). Optional later: Prefect, a thin Streamlit/Gradio UI, query logs.

**Out of scope for 30 days:** Spark, Kafka, Kubernetes, dbt, Snowflake, fine-tuning, training loops, a second product.

**Tables we will model (Day 4, not today):** `documents`, `chunks`, `embeddings`, `query_logs`, `eval_results`.
