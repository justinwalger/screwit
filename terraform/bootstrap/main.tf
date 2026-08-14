terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Separate state/prefix from the root config on purpose - this is only ever
  # applied manually by a privileged identity, never by CI. See README notes
  # in ../main.tf for why it can't be merged back into the CI-managed config.
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = "europe-west1"
}

resource "google_artifact_registry_repository" "screwit" {
  location      = "europe-west1"
  repository_id = "screwit"
  format        = "DOCKER"

  # Every push to main tags a new backend+frontend image by commit SHA and
  # nothing else removes old ones, so without this the repo grows unbounded.
  # Always keep the 2 most recent versions (rollback safety net) regardless
  # of age, and delete anything else once it's older than 30 days.
  cleanup_policies {
    id     = "keep-minimum-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 2
    }
  }

  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      tag_state  = "ANY"
      older_than = "259200s" # 3 days
    }
  }
}

# Dedicated identity for the GitHub Actions deploy workflow (terraform/main.tf).
# Deliberately scoped to *not* include IAM-granting permissions on itself or
# the project, so a compromised/leaked CI credential can't escalate privilege -
# that's also why these grants have to live here, applied by a human, instead
# of in the CI-managed config.
resource "google_service_account" "ci_deployer" {
  account_id   = "github-actions-deployer"
  display_name = "CI/CD deployer for GitHub Actions"
}

resource "google_artifact_registry_repository_iam_member" "ci_deployer_writer" {
  location   = google_artifact_registry_repository.screwit.location
  repository = google_artifact_registry_repository.screwit.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.ci_deployer.email}"
}

resource "google_project_iam_member" "ci_deployer_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.ci_deployer.email}"
}

# Lets the deployer act as the Cloud Run services' runtime identity when deploying.
resource "google_project_iam_member" "ci_deployer_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.ci_deployer.email}"
}

# The deploy workflow's `terraform init -backend-config="bucket=..."` runs as this
# SA and needs to list/read/write/lock objects in the state bucket - scoped to just
# this bucket, not project-wide storage access.
resource "google_storage_bucket_iam_member" "ci_deployer_state_access" {
  bucket = var.state_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ci_deployer.email}"
}

resource "google_service_account_key" "ci_deployer_key" {
  service_account_id = google_service_account.ci_deployer.name
}

output "ci_deployer_key" {
  description = "Base64-encoded SA key JSON. Decode with: terraform output -raw ci_deployer_key | base64 -d"
  value       = google_service_account_key.ci_deployer_key.private_key
  sensitive   = true
}
