variable "project_id" {
  type        = string
  description = "Existing GCP project ID (create outside Terraform if you lack org permissions)."
}

variable "region" {
  type        = string
  description = "Primary region for Cloud SQL, Cloud Run, and GCS."
  default     = "us-east1"
}

variable "billing_account" {
  type        = string
  description = "Billing account ID for the $25 budget (format XXXXXX-XXXXXX-XXXXXX)."
}

variable "budget_amount_usd" {
  type        = number
  description = "Hard planning cap. Alerts fire inside this amount."
  default     = 25
}

variable "budget_email" {
  type        = string
  description = "Who receives 50% and 80% budget threshold emails."
}

variable "cloud_sql_activation_policy" {
  type        = string
  description = "ALWAYS while working/demoing; NEVER (stopped) otherwise. NEVER is the $25 default."
  default     = "NEVER"

  validation {
    condition     = contains(["ALWAYS", "NEVER"], var.cloud_sql_activation_policy)
    error_message = "Use ALWAYS or NEVER."
  }
}

variable "operator_ip_cidr" {
  type        = string
  description = "Your public IP /32 for Cloud SQL authorized networks. 0.0.0.0/0 is allowed only for short demos."
  default     = "127.0.0.1/32"
}
