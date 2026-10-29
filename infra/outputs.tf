output "corpus_bucket" {
  value = google_storage_bucket.corpus.name
}

output "quarantine_bucket" {
  value = google_storage_bucket.quarantine.name
}

output "cloud_sql_instance" {
  value = google_sql_database_instance.pg.name
}

output "cloud_sql_public_ip" {
  value = google_sql_database_instance.pg.public_ip_address
}

output "cloud_sql_activation_policy" {
  value = var.cloud_sql_activation_policy
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.p1.dataset_id
}

output "ingest_sa" {
  value = google_service_account.ingest.email
}

output "api_sa" {
  value = google_service_account.api.email
}

output "database_url_secret" {
  value = google_secret_manager_secret.database_url.name
}

output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docpipe.repository_id}"
}

output "ingest_job" {
  value = try(google_cloud_run_v2_job.ingest[0].name, "not-created (set ingest_image)")
}

output "api_service" {
  value = try(google_cloud_run_v2_service.api[0].name, "not-created (set api_image)")
}

output "api_uri" {
  value = try(google_cloud_run_v2_service.api[0].uri, "not-created (set api_image)")
}

output "database_socket_secret" {
  value = google_secret_manager_secret.database_socket_url.name
}

output "ci_sa" {
  value = google_service_account.ci.email
}

output "github_wif_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}
