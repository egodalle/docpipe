# Timeline — DocPipe P1 v1.0

| Field | Value |
| --- | --- |
| Document | DOC-005 |
| Version | 1.0 |
| Timezone | America/New_York |
| Kickoff | Monday 2026-10-26 |
| Ship | Saturday 2026-12-06 |

Capacity assumed: ~2 hours on weeknights or a weekend block, totaling 10–12h per calendar week.

```
Oct 26          Nov 2           Nov 9           Nov 16          Nov 23          Nov 30          Dec 6
|---- Week 1 ----|---- Week 2 ----|---- Week 3 ----|---- Week 4 ----|---- Week 5 ----|---- Week 6 ----|
 Kickoff+IaC      Corpus+extract   Chunk+embed      Incremental      /ask API         Eval+v1.0
      M1               M2               M3               M4               M5               M6
```

| Week | Dates | Milestone | Exit criteria |
| --- | --- | --- | --- |
| 1 | Mon 10/26 – Sun 11/01 | M1 Foundations | Cloud SQL up; five tables; Terraform plan clean |
| 2 | Mon 11/02 – Sun 11/08 | M2 Ingest | GCS corpus loaded; hashes in `documents` |
| 3 | Mon 11/09 – Sun 11/15 | M3 Retrieve | Embeddings + HNSW; 5 logged similarity queries |
| 4 | Mon 11/16 – Sun 11/22 | M4 Incremental | One-file edit re-chunks only that doc; Cloud Run job |
| 5 | Mon 11/23 – Sun 11/29 | M5 API | `/ask` returns citations; refusal path |
| 6 | Mon 11/30 – Sat 12/06 | M6 v1.0 | recall@5 in README; tag; demo |

**Critical path:** Cloud SQL (W1) → extract (W2) → embed (W3) → `/ask` (W5) → eval (W6). Incremental (W4) can slip two days without moving the ship date. Eval cannot slip; it is the ship gate.

**Hold points**

| Date | Hold | Who |
| --- | --- | --- |
| 2026-11-01 | M1 review — stop if billing/API blocked | Engineer |
| 2026-11-22 | M4 review — drop W5-4 hybrid if job is not in GCP | Engineer |
| 2026-12-06 | Ship / no-ship | Sponsor (self) |

**Holidays:** US Thanksgiving week is Week 5 (Nov 23–29). Plan API work as a weekend block if Thursday is unavailable. Do not start new scope that week.
