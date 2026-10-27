# RAID log — DocPipe P1

| Field | Value |
| --- | --- |
| Document | DOC-006 |
| Status | Live |
| Last updated | 2026-10-27 night (M7 v1.0) |

## Risks

| ID | Risk | L | I | Mitigation | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Cloud SQL spend exceeds $25 | H | H | `db-f1-micro`, no HA, `activation_policy=NEVER` by default; alerts $10/$20 | Ed | Open |
| R2 | Vertex quota or model alias changes | M | H | Embeddings pinned `text-embedding-004` dim 768; generation pinned `gemini-3-flash-preview` / `global` (ADR 0003 D5) | Ed | Open (quota) |
| R3 | PDF extract quality tanks recall | M | M | Prefer markdown in seed corpus | Ed | Open |
| R6 | Scope creep | H | H | Charter §5; 7-day cut list | Ed | Open |
| R7 | 7-day schedule slip | H | H | Cut hybrid (already); cut WIF; eval still ships | Ed | Closed — v1.0 tagged 2026-10-27 |
| R8 | Dataform assertions fail with empty BQ | M | L | Seeded `ingest_runs` + `eval_results` on D6; CLI 4/4 green | Ed | Closed |

## Assumptions

| ID | Assumption | Validate by |
| --- | --- | --- |
| A1 | Billing account can own `docpipe-p1` | **True** — billed; `$25` budget exists |
| A3 | 20–50 files can hit recall@5 ≥ 0.70 | **True** — 28/28 unique docs, 27/28 raw |
| A4 | Local :5433 stays free for dev | True |
| A6 | Unlimited hours this week are actually available | Daily status |

## Issues

| ID | Issue | Opened | Status |
| --- | --- | --- | --- |
| I1 | Day-2 SQL never committed | 2026-10-26 | **Closed** in `b320b65` |
| I2 | Homebrew Postgres occupies :5432 | 2026-09-22 | Accepted — DocPipe on :5433 |
| I3 | Six-week GitHub issues stale after sprint change | 2026-10-26 | **Closed** — D1–D7 are #7–#13 |
| I4 | Billing quota exceeded; `docpipe-p1` has no billing | 2026-10-26 | **Closed** — unlinked `beaming-theorem-435112-r8`; linked `docpipe-p1` |
| I5 | D1 `infra/` + `dataform/` uncommitted on `main` | 2026-10-26 | **Closed** in `29ba223` |
| I6 | D2 ingest pack (`src/`, `tests/`, `data/licenses.csv`) uncommitted | 2026-10-26 | **Closed** this commit — GitHub #8 closing |
| I7 | D3+D4 pack uncommitted on `main` | 2026-10-26 | **Closed** this commit — GitHub #9 and #10 closing |
| I8 | `gemini-2.0-flash` 404 (shut down 2026-06-01) | 2026-10-27 | **Closed** — pinned `gemini-3-flash-preview` / `global` |
| I9 | D5 API pack uncommitted on `main` | 2026-10-27 | **Closed** this commit — GitHub #11 closing |
| I10 | D6 eval pack uncommitted on `main` | 2026-10-27 | **Closed** this commit — GitHub #12 closing |
| I11 | Cloud Run container missed `config.yaml` after pip install | 2026-10-27 | **Closed** — `DOCS_ROOT`/`DOCS_CONFIG` + `_repo_root()` |

## Dependencies

| ID | Dependency | Needed | Notes |
| --- | --- | --- | --- |
| D1 | GCP project + billing | D1 | **Done** — `docpipe-p1` billed; `$25` budget exists |
| D2 | Vertex AI API | D3 | **Done** — `aiplatform.googleapis.com` enabled; first embed 2026-10-26 |
| D3 | Golden questions | D6 | **Done** — `eval/golden.json` 28 items; recall@5 1.000 |
