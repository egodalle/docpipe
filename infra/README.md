# Terraform — DocPipe P1

Creates GCS, Cloud SQL (`db-f1-micro`, **stopped by default**), BigQuery, IAM, Secret Manager, and a **$25** billing budget.

```bash
gcloud config set project YOUR_PROJECT
cp terraform.tfvars.example terraform.tfvars   # edit project_id, billing_account, budget_email, operator_ip_cidr
terraform init
terraform plan
terraform apply
```

Start Cloud SQL only while working:

```hcl
cloud_sql_activation_policy = "ALWAYS"
```

Then set it back to `NEVER` and apply. Do not leave ALWAYS on overnight — that is how you spend the $25 cap.

Cloud Run job/service come in D4/D7; this stack is D1 foundations.
