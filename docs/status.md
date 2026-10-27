# Status — DocPipe P1

Living document. Newest entry at the top.

## Current

| Field | Value |
| --- | --- |
| Phase | **D6 / M6 complete.** Next is **D7 ship** (Sun 11/02) |
| Date | 2026-10-27 |
| Ship | 2026-11-02 |
| Cost cap | $25 |
| GCP project | `docpipe-p1` (number `129492415939`) ACTIVE |
| Cloud SQL | `docpipe-pg` **STOPPED** / `NEVER` |
| Local DB | 36 live docs, 188 chunks, 188 embeddings on `:5433` |
| Model | embed `text-embedding-004` dim **768**; generate `gemini-3-flash-preview` (global) |
| Index | `embeddings_hnsw` (cosine) + unique-document collapse (`pool_k=15`) |
| Eval | recall@5 **1.000** (28/28 unique docs) vs 0.964 raw; Dataform 4/4 green |
| API | `127.0.0.1:8080` `/ask` `/health` `/stats` |
| Blocker | None |
| Next | D7 Cloud Run service + tag v1.0. Leave SQL stopped. |

## 2026-10-27 night — M6 eval + Dataform (ahead of calendar)

- `eval/golden.json`: 28 questions. Harness `docpipe eval`. Winner persisted as `eval-unique-d6`.
- Tune: unique-document collapse vs raw top-5. Raw **0.964** (27/28, miss=`mvcc`). Unique **1.000** (28/28). Adopted `eval.unique_documents: true`.
- Dataform CLI 4/4 passed on BQ: `recall_at_5`, `empty_extract_rate`, `cited_or_refused`, `incremental_noop`.
- pytest 31 passed. Cloud SQL left **STOPPED**. GitHub #12 closing with this commit.

## 2026-10-27 00:51 — D5 test run

- pytest **27 passed** in 3.85s (`reports/d5-pytest.txt`, `reports/d5-junit.xml`, `reports/d5-report.html`).
- Live API **6/6 passed** on `127.0.0.1:8080` (`reports/d5-live-api.txt`): health, stats 36/188/188, JSONB cited score 0.755, weather refused, sourdough refused, 2001-char question HTTP 422.
- Cloud SQL not used.

## 2026-10-27 night — M5 API (ahead of calendar)

- FastAPI `POST /ask`, `GET /health`, `GET /stats`. `docpipe serve` on `:8080`.
- Refusal when top score < 0.60; question cap 2000 chars; k cap 8. Two off-topic asks refused (weather, sourdough). JSONB ask cited `datatype-json.html` score 0.755.
- Generation pinned to `gemini-3-flash-preview` / `global` (ADR 0003). `gemini-2.0-flash` shut down 2026-06-01.
- `query_logs` in Postgres and BigQuery `docpipe_p1.query_logs` (cited + two refused).
- pytest 27 passed. Cloud SQL left **STOPPED**. GitHub #11 closing with this commit.

## 2026-10-26 night — M4 incremental (ahead of calendar)

- Hash sync: insert / update (tombstone old live row + new hash) / tombstone missing files. `docpipe sync` then re-chunks **only** the changed document.
- pytest 21 passed. Fail-the-job: empty body, dim, duplicate live hash, chunks left on tombstoned docs.
- Cloud Run job `docpipe-ingest` in `infra/run.tf` (created when `ingest_image` is set). Artifact Registry `docpipe`. Do not execute the job while SQL is NEVER.
- Cloud SQL left **STOPPED**. GitHub #10 closing with this commit.

## 2026-10-26 night — M3 retrieve (ahead of calendar)

- Chunker `recursive_400_80`: 188 chunks stored (token_count 40–480, 0 empty bodies).
- Vertex batch embed on `docpipe-p1` / `us-east1`. Live dim 768 matches SQL. Skip-known-hash: second `docpipe index` was `chunked=0 embedded=0 skipped=36`.
- HNSW `embeddings_hnsw`; SQL+Python `search_chunks`. Five queries logged in `query_logs` (question + chunk_ids + scores; no LLM answer).
- pytest: 18 passed (chunker, dim, skip-known-hash, empty body CHECK, duplicate live hash).
- Cloud SQL left **STOPPED**. GitHub #9 closing with this commit.

## 2026-10-26 night — M2 ingest

- `data/licenses.csv`: 36 redistributable files (PostgreSQL / MIT).
- `docpipe fetch` → `data/raw/` (gitignored). `docpipe ingest` → 36 live rows, 0 quarantined, empty-extract rate 0%.
- pytest: 6 passed (extract, licenses size, nonempty load, quarantine fail-rate).
- Corpus copied to GCS. Cloud SQL left **STOPPED**.
- I6 closed; GitHub #8 closing with this commit.

## 2026-10-26 night — M1 shipped

- Local compose pgvector on 5433: `documents`, `chunks`, `embeddings`, `query_logs`, `eval_results`.
- `terraform apply` complete. GCS corpus/quarantine, BigQuery `docpipe_p1` + assertions, ingest/API SAs, `$25` budget, Dataform agent IAM, Secret Manager `docpipe-database-url`.
- Cloud SQL created runnable (GCP cannot create `NEVER`), then patched to **NEVER**. Confirmed `STOPPED`.
- GitHub #7 closed. #8–#13 remain D2–D7.
- D1 Terraform/Dataform files committed to `main` (closes RAID I5).

## 2026-10-26 evening

- Schedule compressed to 7 days (ADR 0005). Cost cap $25.
- Dataform added as warehouse tests (ADR 0006). pytest still owns the job.
- I1 (Day-2 SQL uncommitted) **closed** — shipped in `b320b65`.

## Log

| Day | Date | Hours | Milestone | Notes |
| --- | --- | --- | --- | --- |
| 0 | 2026-10-26 | — | Kickoff docs | Six-week plan, then amended |
| D1 | 2026-10-26 | evening | **M1 done** | Local schema + GCP skeleton; SQL stopped |
| D2 | 2026-10-26 | night | **M2 done** | 36 licensed files; hashes in `documents`; pytest green |
| D3 | 2026-10-26 | night | **M3 done** | 188 chunks + embeddings; HNSW; 5 logged queries |
| D4 | 2026-10-26 | night | **M4 done** | Hash sync; fail-the-job tests; Cloud Run job TF |
| D5 | 2026-10-27 | night | **M5 done** | `/ask` citations + refusal; logs in BQ |
| D6 | 2026-10-27 | night | **M6 done** | recall@5 1.000; Dataform 4/4; unique-docs adopted |
