resource "google_sql_database_instance" "pg" {
  name             = "docpipe-pg"
  database_version = "POSTGRES_16"
  region           = var.region

  deletion_protection = false

  settings {
    # ENTERPRISE (not ENTERPRISE_PLUS) is required for shared-core db-f1-micro.
    edition           = "ENTERPRISE"
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_type         = "PD_HDD"
    disk_size         = 10
    # GCP cannot CREATE a stopped instance. Create runnable, then patch below.
    activation_policy = "ALWAYS"

    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "operator"
        value = var.operator_ip_cidr
      }
    }

    backup_configuration {
      enabled = false
    }
  }

  timeouts {
    create = "40m"
    update = "20m"
  }

  lifecycle {
    ignore_changes = [settings[0].activation_policy]
  }

  depends_on = [google_project_service.required]
}

resource "google_sql_database" "docpipe" {
  name     = "docpipe"
  instance = google_sql_database_instance.pg.name
}

resource "google_sql_user" "docpipe" {
  name     = "docpipe"
  instance = google_sql_database_instance.pg.name
  password = random_password.db.result
}

resource "random_password" "db" {
  length  = 24
  special = false
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "docpipe-database-url"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id
  secret_data = format(
    "postgresql://docpipe:%s@%s:5432/docpipe",
    random_password.db.result,
    google_sql_database_instance.pg.public_ip_address,
  )
}

# Stop (or start) after the instance, database, and user exist.
resource "terraform_data" "sql_activation" {
  depends_on = [
    google_sql_database.docpipe,
    google_sql_user.docpipe,
    google_secret_manager_secret_version.database_url,
  ]

  triggers_replace = [var.cloud_sql_activation_policy]

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = "gcloud sql instances patch ${google_sql_database_instance.pg.name} --activation-policy=${var.cloud_sql_activation_policy} --project=${var.project_id} --quiet"
  }
}
