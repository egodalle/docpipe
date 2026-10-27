resource "google_storage_bucket" "corpus" {
  name                        = "docpipe-p1-corpus-${data.google_project.current.number}"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  labels = {
    project = "docpipe"
    phase   = "p1"
  }

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket" "quarantine" {
  name                        = "docpipe-p1-quarantine-${data.google_project.current.number}"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  labels = {
    project = "docpipe"
    phase   = "p1"
  }

  depends_on = [google_project_service.required]
}
