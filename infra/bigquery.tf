resource "google_bigquery_dataset" "p1" {
  dataset_id                 = "docpipe_p1"
  location                   = var.region
  delete_contents_on_destroy = true
  description                = "Analytics copies of ingest_runs, query_logs, eval_results. Postgres is the system of record."

  labels = {
    project = "docpipe"
    phase   = "p1"
  }

  depends_on = [google_project_service.required]
}

resource "google_bigquery_dataset" "assertions" {
  dataset_id                 = "docpipe_p1_assertions"
  location                   = var.region
  delete_contents_on_destroy = true
  description                = "Dataform assertion results."

  labels = {
    project = "docpipe"
    phase   = "p1"
  }

  depends_on = [google_project_service.required]
}
