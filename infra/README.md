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

Cloud Run **job** `docpipe-ingest` is defined in `run.tf` but not created until `ingest_image` is set (image must exist in Artifact Registry). SQL stays **stopped** unless you are working.

```bash
# after docker build/push
ingest_image = "us-east1-docker.pkg.dev/docpipe-p1/docpipe/ingest:d4"
terraform apply
```

Do not execute the job while Cloud SQL is NEVER — the job cannot reach a stopped instance.
