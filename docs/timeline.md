# Timeline — DocPipe P1 v1.0 (7-day sprint)

| Field | Value |
| --- | --- |
| Document | DOC-005 |
| Version | 1.1 |
| Timezone | America/New_York |
| Kickoff | Monday 2026-10-26 |
| Ship | Sunday 2026-11-02 |

```
Oct 26      27      28      29      30      31     Nov 1     Nov 2
|-- D1 TF --|-- D2 extract --|-- D3 embed --|-- D4 sync --|-- D5 API --|-- D6 eval+Dataform --|-- D7 ship --|
    M1            M2              M3             M4            M5              M6                 v1.0
```

| Day | Date | Milestone | Exit criteria |
| --- | --- | --- | --- |
| D1 | Mon 10/26 – Tue 10/27 | M1 Foundations | Terraform plan clean; five tables local; Cloud SQL exists **stopped** |
| D2 | Wed 10/28 (done 10/26) | M2 Ingest | Corpus in GCS; hashes in `documents` |
| D3 | Thu 10/29 | M3 Retrieve | Embeddings + HNSW; 5 similarity queries |
| D4 | Fri 10/30 | M4 Incremental | One-file re-chunk; pytest fail-the-job |
| D5 | Sat 10/31 | M5 API | `/ask` citations + refusal |
| D6 | Sun 11/01 | M6 Eval | recall@5 in README; Dataform assertions green |
| D7 | Sun 11/02 | M7 v1.0 | Tag; Cloud SQL stopped; spend ≤ $25 |

**Critical path:** Terraform (D1) → extract (D2) → embed (D3) → `/ask` (D5) → eval + Dataform (D6). Incremental (D4) can overlap D5 by a few hours. Eval cannot slip past D7.

**Hold:** 2026-10-27 EOD — **cleared** 2026-10-26 night. Billing linked; `terraform apply` done; Cloud SQL `docpipe-pg` **STOPPED**. Do not start SQL overnight.

**D1 result:** M1 met (local five tables + GCP skeleton + SQL stopped).

**D2 result:** M2 met 2026-10-26 (ahead of calendar). 36 licensed files in GCS; 36 live `documents` on :5433; pytest green. Next is D3 (Thu 10/29) chunk + Vertex.

**D3 result:** M3 met 2026-10-26 (ahead of calendar). 188 chunks + 188 `text-embedding-004` vectors (dim 768) on :5433; `embeddings_hnsw`; five queries in `query_logs`. Cloud SQL stayed **STOPPED**.

**D4 result:** M4 met 2026-10-26 (ahead of calendar). Hash sync insert/update/tombstone; one-file edit reindexes only that doc; pytest 21; Cloud Run job TF gated on `ingest_image`. Next is D5 `/ask`.

**D5 result:** M5 met 2026-10-27 (ahead of calendar). Local `/ask` citations + refusal; `query_logs` in Postgres and BQ; Gemini `gemini-3-flash-preview` on `global`. Cloud SQL stayed **STOPPED**. Next is D6 eval.
