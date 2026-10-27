# Status — DocPipe P1

Living document. Newest entry at the top.

## Current

| Field | Value |
| --- | --- |
| Phase | **D1 / M1 complete.** Next is **D2 ingest** (Wed 10/28) |
| Date | 2026-10-26 |
| Ship | 2026-11-02 |
| Cost cap | $25 |
| GCP project | `docpipe-p1` (number `129492415939`) ACTIVE |
| Cloud SQL | `docpipe-pg` **STOPPED** (`activation_policy = NEVER`, `db-f1-micro` ENTERPRISE) |
| Local DB | Docker pgvector `:5433` — five tables |
| Blocker | None |
| Next | D2 corpus + extract (Wed 10/28). Leave Cloud SQL stopped. |

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
| D2 | 2026-10-28 | | M2 | Corpus + extract — not started |
