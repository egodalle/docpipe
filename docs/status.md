# Status — DocPipe P1

Living document. Newest entry at the top.

## Current

| Field | Value |
| --- | --- |
| Phase | **D2 / M2 complete.** Next is **D3 chunk + embed** (Thu 10/29) |
| Date | 2026-10-26 |
| Ship | 2026-11-02 |
| Cost cap | $25 |
| GCP project | `docpipe-p1` (number `129492415939`) ACTIVE |
| Cloud SQL | `docpipe-pg` **STOPPED** / `NEVER` (reconfirmed 2026-10-26 22:19) |
| Local DB | 36 live `documents` on `:5433` (32 postgres-docs, 4 pgvector) |
| GCS | `gs://docpipe-p1-corpus-129492415939/raw/` 36 files + `licenses.csv` |
| Blocker | None |
| Next | D3 (`recursive_400_80` + Vertex). Leave SQL stopped until embed. |

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
