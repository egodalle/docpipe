data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_service" "required" {
  for_each = toset([
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
    "bigquery.googleapis.com",
    "dataform.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "billingbudgets.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
