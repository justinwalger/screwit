variable "project_id" {
  description = "gcp project id"
  type        = string
}

variable "state_bucket_name" {
  description = "GCS bucket holding the root config's (terraform/main.tf) Terraform state - the one created manually in step 1 of the README's Deployment setup."
  type        = string
}
