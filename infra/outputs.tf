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
