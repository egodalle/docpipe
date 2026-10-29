# Architecture decision records

Format: title, status, context, decision, consequences. Numbers are append-only.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-vector-store-cloud-sql-pgvector.md) | Cloud SQL Postgres + pgvector, not Vertex Vector Search | Accepted |
| [0002](0002-compute-cloud-run.md) | Cloud Run job + service, not GKE | Accepted |
| [0003](0003-models-vertex.md) | Vertex embeddings + Gemini Flash, one each | Accepted |
| [0004](0004-prototype-to-gcp.md) | Keep v0 repo; lift to GCP; do not restart a tutorial | Accepted |
| [0005](0005-seven-day-sprint.md) | Compress P1 to 7 days; $25 cap | Accepted |
| [0006](0006-dataform-for-warehouse-tests.md) | Dataform assertions on BigQuery; pytest keeps the job | Accepted |
| [0007](0007-hybrid-rrf.md) | Hybrid lexical + vector RRF in Postgres | Accepted |
| [0008](0008-refuse-eval-citation-integrity.md) | Refuse golden set + citation integrity on `/ask` | Accepted |
| [0009](0009-dynamic-corpus-path.md) | Local UI/API can switch the corpus directory | Accepted |
| [0010](0010-github-dataform-wif.md) | GitHub Actions WIF runs Dataform on merge to main | Accepted |
