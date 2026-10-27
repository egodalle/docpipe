# Delivery plan — DocPipe P1 v1.0 (7-day sprint)

| Field | Value |
| --- | --- |
| Document | DOC-004 |
| Version | 1.1 |
| Status | Approved |
| Date | 2026-10-26 |
| Calendar | [timeline.md](timeline.md) |
| Supersedes | v1.0 six-week WBS |

## 1. RACI

Unchanged: Ed is R/A on engineering, cost, and ship.

## 2. Cadence

- **Window:** 2026-10-26 → 2026-11-02.
- **Hours:** unlimited. Still cut scope rather than silent overtime on hybrid search.
- **Stand-up:** update [status.md](status.md) at the end of each day.
- **Cost:** $25 cap; budget alerts at $10 and $20; stop Cloud SQL when idle.

## 3. Work breakdown (days)

### D1 — Foundations + Terraform · 2026-10-26 / 27

| ID | Work | Done when |
| --- | --- | --- |
| D1-1 | Charter v1.1, ADRs 0005–0006 | This pack in git |
| D1-2 | Terraform: APIs, GCS, Secret Manager, SAs, BQ, Dataform IAM, $25 budget | `terraform plan` clean |
| D1-3 | Cloud SQL `db-f1-micro` + pgvector, **stopped** | Instance exists, not billing CPU |
| D1-4 | `sql/001_init.sql` + local `docker compose` pgvector | Five tables on :5433 |

**Milestone M1:** Schema local + GCP skeleton via Terraform.

### D2 — Corpus + extract · 2026-10-28

| ID | Work | Done when |
| --- | --- | --- |
| D2-1 | 20–50 licensed files in `data/raw` and GCS | `licenses.csv` complete |
| D2-2 | Extractors + pydantic + hashes into `documents` | Rows present |
| D2-3 | Quarantine + pytest non-empty load | Green tests |

**Milestone M2:** `documents` populated.

### D3 — Chunk + embed + index · 2026-10-29

| ID | Work | Done when |
| --- | --- | --- |
| D3-1 | One chunker (`recursive_400_80`) | Chunks stored |
| D3-2 | Freeze Vertex embedding model; batch embed; skip known hashes | `embeddings` filled |
| D3-3 | HNSW + `search_chunks` | 5 logged hits |

**Milestone M3:** Neighbors out. No LLM yet.

### D4 — Incremental + job tests · 2026-10-30

| ID | Work | Done when |
| --- | --- | --- |
| D4-1 | Hash sync insert / update / tombstone | One-file edit only |
| D4-2 | pytest fails the job on empty/dim/dupes/orphans | Bad fixture fails |
| D4-3 | Cloud Run job definition in Terraform | Job deployable |

**Milestone M4:** Incremental ingest.

### D5 — API · 2026-10-31

| ID | Work | Done when |
| --- | --- | --- |
| D5-1 | FastAPI `/ask` `/health` `/stats` | Three curl examples |
| D5-2 | Refusal threshold + caps | Two refuse questions |
| D5-3 | `query_logs` in Postgres + ship to BigQuery | Last asks in BQ |

**Milestone M5:** Cited API.

### D6 — Eval + Dataform · 2026-11-01

| ID | Work | Done when |
| --- | --- | --- |
| D6-1 | `eval/golden.json` 20–30 + harness + `eval/baseline.md` | recall@5 number |
| D6-2 | One-variable tune; adopt winner | Before/after in README |
| D6-3 | Dataform assertions run against BQ | CLI exit 0 |

**Milestone M6:** Measured quality.

### D7 — Ship · 2026-11-02

| ID | Work | Done when |
| --- | --- | --- |
| D7-1 | Cloud Run service in Terraform; README true | Stranger path works |
| D7-2 | Tag `v1.0`; demo clip; cost screenshot < $25 | Milestone closed |
| D7-3 | Stop Cloud SQL | `activation_policy = NEVER` |

**Milestone M7 / v1.0:** Charter §2.

## 4. Cut list (if a day slips)

1. Hybrid search (already cut)
2. Second chunk strategy
3. GitHub Actions WIF (run eval locally, document it)
4. Demo recording (README + curl remain)

Never cut: Terraform, hashes, fail-the-job pytest, Dataform assertions, refusal path, eval number, Cloud SQL stop-when-idle.

## 5. Test split

| Layer | Tool | What it proves |
| --- | --- | --- |
| Job / API | pytest | Extract, schema, hashes, dim, refusal |
| Warehouse | Dataform | Rates and eval gates on BigQuery copies |
