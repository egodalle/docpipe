# Dataform warehouse tests

These assertions run **against BigQuery**, not against Postgres. pytest still tests the Python job.

```bash
cd dataform
npm install
# ADC credentials, gitignored. Create dataform/.df-credentials.json:
# { "projectId": "docpipe-p1", "location": "us-east1" }
npx dataform compile
npx dataform run
```

Use the local `@dataform/cli` from `package.json` (3.0.71). `npx @dataform/cli@3.0.23` fails on Node 25 (missing `uuid`).

D6 seeded `ingest_runs` and wrote `eval_results` from `docpipe eval`. `query_logs` came from D5 `/ask`.

| Assertion | Gate |
| --- | --- |
| `empty_extract_rate` | Latest ingest empty-extract rate < 5% |
| `recall_at_5` | Latest eval run ≥ 0.70 |
| `cited_or_refused` | Non-refused answers have citations |
| `incremental_noop` | Unchanged corpus ⇒ 0 files reprocessed |

Merge to `main` runs the same commands in GitHub Actions as `sa-docpipe-ci` (Workload Identity Federation, [ADR 0010](../docs/adr/0010-github-dataform-wif.md)). Pull requests compile only. Cloud SQL is not used.

Hosted Dataform Git linking stays off: SQLX lives under `dataform/`, and hosted compile expects `dataform.json` at the repo root. BigQuery `docpipe_p1_assertions` is where a merge shows up in GCP.
