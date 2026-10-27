# Warehouse tests are the SQLX files in ../dataform/, run with:
#   npx @dataform/cli run --timeout 10m
# Hosted Dataform Git linking needs a GitHub PAT in Secret Manager — out of
# P1 v1.0 (ADR 0006). Terraform still enables the API and grants the default
# Dataform service agent access to the datasets so a later hosted repo works.

resource "google_project_service_identity" "dataform" {
  provider = google-beta
  project  = var.project_id
  service  = "dataform.googleapis.com"

  depends_on = [google_project_service.required]
}

resource "time_sleep" "dataform_identity" {
  create_duration = "30s"
  depends_on      = [google_project_service_identity.dataform]
}

resource "google_bigquery_dataset_iam_member" "dataform_p1" {
  dataset_id = google_bigquery_dataset.p1.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_project_service_identity.dataform.email}"
  depends_on = [time_sleep.dataform_identity]
}

resource "google_bigquery_dataset_iam_member" "dataform_assertions" {
  dataset_id = google_bigquery_dataset.assertions.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_project_service_identity.dataform.email}"
  depends_on = [time_sleep.dataform_identity]
}

resource "google_project_iam_member" "dataform_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_project_service_identity.dataform.email}"
  depends_on = [time_sleep.dataform_identity]
}
