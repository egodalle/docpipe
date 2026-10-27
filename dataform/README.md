# Dataform warehouse tests

These assertions run **against BigQuery**, not against Postgres. pytest still tests the Python job.

```bash
cd dataform
# set defaultDatabase in dataform.json to your GCP project ID
npx @dataform/cli install
npx @dataform/cli compile
npx @dataform/cli run
```

Assertions fail until D4–D6 have shipped `ingest_runs`, `query_logs`, and `eval_results` into `docpipe_p1`. That is expected on D1.

| Assertion | Gate |
| --- | --- |
| `empty_extract_rate` | Latest ingest empty-extract rate < 5% |
| `recall_at_5` | Latest eval run ≥ 0.70 |
| `cited_or_refused` | Non-refused answers have citations |
| `incremental_noop` | Unchanged corpus ⇒ 0 files reprocessed |

Hosted Dataform Git linking is out of P1 v1.0 (ADR 0006). Terraform enables the API and IAM so it can be added later.
