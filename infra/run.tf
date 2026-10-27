resource "google_artifact_registry_repository" "docpipe" {
  location      = var.region
  repository_id = "docpipe"
  description   = "DocPipe ingest/API images"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "google_artifact_registry_repository_iam_member" "ingest_reader" {
  location   = google_artifact_registry_repository.docpipe.location
  repository = google_artifact_registry_repository.docpipe.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.ingest.email}"
}

resource "google_cloud_run_v2_job" "ingest" {
  count    = var.ingest_image == "" ? 0 : 1
  name     = "docpipe-ingest"
  location = var.region

  deletion_protection = false

  template {
    template {
      service_account = google_service_account.ingest.email
      timeout         = "3600s"
      max_retries     = 1

      containers {
        image   = var.ingest_image
        command = ["docpipe"]
        args    = ["sync"]

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.pg.connection_name]
        }
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_artifact_registry_repository.docpipe,
    google_secret_manager_secret_version.database_url,
  ]
}