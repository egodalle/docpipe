# RAID log — DocPipe P1

| Field | Value |
| --- | --- |
| Document | DOC-006 |
| Status | Live |
| Last updated | 2026-10-26 |

## Risks

| ID | Risk | L | I | Mitigation | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Cloud SQL bill exceeds $90/mo | M | H | Smallest non-HA instance; stop when not demoing; budget alert $50 | Ed | Open |
| R2 | Vertex quota or model alias changes mid-eval | M | H | Pin model IDs in config week 3; re-embed only if forced (ADR 0003 amendment) | Ed | Open |
| R3 | PDF extract quality tanks recall | M | M | Prefer markdown in the seed corpus; quarantine scans; measure empty-extract rate | Ed | Open |
| R4 | Thanksgiving week (W5) slips the API | M | H | Pre-write OpenAPI schema in W4; cut hybrid search | Ed | Open |
| R5 | Workload Identity Federation blocks CI | L | M | Local eval remains the ship gate; CI is best-effort in W6 | Ed | Open |
| R6 | Scope creep (agents, UI, Dataflow) | H | H | Charter §5; cut list in delivery plan | Ed | Open — watch |

Likelihood/impact: L/M/H.

## Assumptions

| ID | Assumption | Validate by |
| --- | --- | --- |
| A1 | A GCP billing account is available in week 1 | W1-1 |
| A2 | Seed Postgres/pgvector docs are redistributable | W2-1 licenses.csv |
| A3 | 20–50 files are enough for recall@5 ≥ 0.70 | W6-1; if not, add files not features |
| A4 | Port 5433 local Postgres remains free for dev | Already true as of 2026-09-22 |
| A5 | 10–12h/week is available through 2026-12-06 | Status updates |

## Issues

| ID | Issue | Opened | Status |
| --- | --- | --- | --- |
| I1 | Day-2 SQL (`sql/`, `notes/`, README) never committed to GitHub | 2026-10-26 | Open — include in first P1 commit |
| I2 | Homebrew Postgres still occupies host :5432 | 2026-09-22 | Accepted — DocPipe stays on :5433 |

## Dependencies

| ID | Dependency | Needed | Notes |
| --- | --- | --- | --- |
| D1 | GCP project + billing | W1 | Blocks Terraform |
| D2 | Vertex AI API enablement | W3 | Blocks embeddings |
| D3 | Golden questions (need a real corpus) | W6 | Cannot write before W2 |
| D4 | GitHub public visibility | W6 | Repo is private today |
