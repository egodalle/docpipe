# Delivery plan — DocPipe P1 v1.0

| Field | Value |
| --- | --- |
| Document | DOC-004 |
| Version | 1.0 |
| Status | Approved |
| Date | 2026-10-26 |
| Calendar | [timeline.md](timeline.md) |

## 1. RACI

Solo project, still named.

| Activity | Engineer (Ed) | Sponsor (Ed / career) | Hiring-manager reader |
| --- | --- | --- | --- |
| Charter / ADRs | A/R | C | I |
| Terraform / IAM | R | A (cost cap) | I |
| Pipeline + tests | R | I | I |
| Eval numbers | R | A (ship gate) | C (must be in README) |
| Public repo + demo | R | A | C |

R = responsible, A = accountable, C = consulted, I = informed.

## 2. Cadence

- **Capacity:** 10–12 hours/week, six weeks (~70 hours). If a week slips, cut the week-5 hybrid-search stretch before cutting eval.
- **Stand-up:** update [status.md](status.md) at the end of each week (blockers, hours, metric).
- **Change control:** stack changes need an ADR; metric slips go in [raid.md](raid.md).

## 3. Work breakdown

Hours are estimates, not commitments.

### Week 1 — Foundations (12h) · 2026-10-26 → 2026-11-01

| ID | Work | Hours | Done when |
| --- | --- | --- | --- |
| W1-0 | Kickoff docs (this pack) | 3 | Charter, ADRs, plan in git |
| W1-1 | GCP project `docpipe-p1`, APIs, billing budget alert $50 | 2 | Project exists; budget alert on |
| W1-2 | Terraform skeleton: project services, GCS, Secret Manager, SA | 4 | `terraform plan` clean |
| W1-3 | Cloud SQL Postgres 16 + pgvector; `sql/001_init.sql` | 3 | `\dt` shows five tables |

**Milestone M1:** Schema exists on Cloud SQL. No embeddings yet.

### Week 2 — First real ingest (12h) · 2026-11-02 → 2026-11-08

| ID | Work | Hours | Done when |
| --- | --- | --- | --- |
| W2-1 | Seed corpus 20–50 files + `licenses.csv` in GCS | 3 | Prefix listed; licenses complete |
| W2-2 | Extractors (md, PDF) + pydantic `Document` / `IngestResult` | 5 | Rows in `documents` with hashes |
| W2-3 | Quarantine path; extract quality log | 2 | Failed files do not crash the job |
| W2-4 | pytest: non-empty load, schema validation | 2 | Tests green locally |

**Milestone M2:** `documents` populated from GCS.

### Week 3 — Chunk + embed + index (12h) · 2026-11-09 → 2026-11-15

| ID | Work | Hours | Done when |
| --- | --- | --- | --- |
| W3-1 | Recursive 400/80 chunker; heading-aware second strategy | 4 | `strategy` column has both |
| W3-2 | Freeze embedding model in config; batch embed; skip known hashes | 5 | `embeddings` filled; dim recorded |
| W3-3 | HNSW index; `search_chunks(query, k, source?)` | 3 | Five hand queries logged |

**Milestone M3:** Neighbors out of Postgres. No LLM yet.

### Week 4 — Incremental + data tests (11h) · 2026-11-16 → 2026-11-22

| ID | Work | Hours | Done when |
| --- | --- | --- | --- |
| W4-1 | Sync: insert / update / tombstone by hash | 5 | Edit one file; only that doc’s chunks change |
| W4-2 | Tests: empty text, dim, dupes, orphans; fail the job | 4 | Intentional bad fixture fails CI locally |
| W4-3 | Cloud Run job definition + Scheduler stub | 2 | Job runs in GCP against Cloud SQL |

**Milestone M4:** Incremental ingest in GCP.

### Week 5 — Serve (11h) · 2026-11-23 → 2026-11-29

| ID | Work | Hours | Done when |
| --- | --- | --- | --- |
| W5-1 | FastAPI `/ask` `/health` `/stats`; citations; request id | 5 | Three curl examples in README |
| W5-2 | Refusal below similarity threshold; token/k caps | 2 | Golden “should refuse” questions pass |
| W5-3 | Persist query_logs; ship to BigQuery | 3 | Last 5 asks queryable in BQ |
| W5-4 | Stretch: hybrid tsvector+RRF — **drop if behind** | 1 | Optional |

**Milestone M5:** Cited API.

### Week 6 — Eval, harden, ship (12h) · 2026-11-30 → 2026-12-06

| ID | Work | Hours | Done when |
| --- | --- | --- | --- |
| W6-1 | `eval/golden.json` 20–30 items; harness; `eval/baseline.md` | 5 | recall@5 number exists |
| W6-2 | One-variable tune; adopt winner in config | 3 | Before/after table in README |
| W6-3 | GitHub Actions: pytest + eval subset via WIF | 2 | Main is green |
| W6-4 | README rewrite, architecture true, tag `v1.0`, 3-min demo | 2 | Public repo or public-ready |

**Milestone M6 / v1.0:** Charter §2.

## 4. Definition of done (release)

See charter §2. Additionally:

- [ ] No secrets in git (`gitleaks` or equivalent cheap check)
- [ ] Cloud SQL can be stopped; README says how to start it for a demo
- [ ] RAID log has no unaccepted P0
- [ ] `eval/baseline.md` matches a run you actually executed

## 5. Cut list (if hours run out)

1. Hybrid search (W5-4)
2. Second chunk strategy serving (keep it stored, don’t eval both)
3. BigQuery shipping (Postgres logs only)
4. Demo recording (keep README + curl)

Never cut: hashes, fail-the-job tests, refusal path, eval number, Terraform.
