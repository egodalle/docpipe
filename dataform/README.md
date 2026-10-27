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

Hosted Dataform Git linking is out of P1 v1.0 (ADR 0006). Terraform enables the API and IAM so it can be added later.
