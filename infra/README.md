# Terraform — DocPipe P1

Creates GCS, Cloud SQL (`db-f1-micro`, **stopped by default**), BigQuery, IAM, Secret Manager, and a **$25** billing budget.

```bash
gcloud config set project YOUR_PROJECT
cp terraform.tfvars.example terraform.tfvars   # edit project_id, billing_account, budget_email, operator_ip_cidr
# terraform.tfvars and *.tfstate stay gitignored — never commit them
terraform init
terraform plan
terraform apply
```

Start Cloud SQL only while working:

```hcl
cloud_sql_activation_policy = "ALWAYS"
```

Then set it back to `NEVER` and apply. Do not leave ALWAYS on overnight — that is how you spend the $25 cap.

Cloud Run **job** `docpipe-ingest` and **service** `docpipe-api` are defined in `run.tf` but not created until `ingest_image` / `api_image` are set (image must exist in Artifact Registry). SQL stays **stopped** unless you are working.

```bash
# after docker build/push (linux/amd64)
api_image    = "us-east1-docker.pkg.dev/docpipe-p1/docpipe/api:v1.0.1"
ingest_image = "us-east1-docker.pkg.dev/docpipe-p1/docpipe/api:v1.0.1"  # optional; same image, command is sync
terraform apply
```

Do not execute the job or expect `/health` 200 while Cloud SQL is NEVER — neither can reach a stopped instance. The API uses Secret Manager `docpipe-database-socket-url` (Cloud SQL Unix socket), not the public-IP URL.
