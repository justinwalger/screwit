terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = "europe-west1"
}

# The Artifact Registry repo, the github-actions-deployer service account, and
# its IAM grants live in ./bootstrap instead of here - the deployer identity
# used to apply this config isn't (and shouldn't be) allowed to manage IAM on
# itself or the project, so those resources have to be applied separately by
# a privileged identity. See terraform/bootstrap/main.tf.

# fastapi backend
resource "google_cloud_run_v2_service" "fastapi_backend" {
  name     = "fastapi-backend"
  location = "europe-west1"
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.backend_image

      env {
        name  = "HF_API_KEY"
        value = var.hf_api_key
      }
      env {
        name  = "HF_MODEL_REPO_ID"
        value = var.hf_model_repo_id
      }
      env {
        name  = "APP_PASSWORD"
        value = var.app_password
      }

      ports {
        container_port = 8080
      }


      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }

        cpu_idle = true
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = google_cloud_run_v2_service.fastapi_backend.project
  location = google_cloud_run_v2_service.fastapi_backend.location
  name     = google_cloud_run_v2_service.fastapi_backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "gradio_frontend" {
  name     = "gradio-frontend"
  location = "europe-west1"
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.frontend_image

      env {
        # No /api prefix - the backend mounts its routes at the root (see
        # src/ui/backend_connector.py, which posts to {backend_api_url}/predict/predict).
        name  = "BACKEND_API_URL"
        value = google_cloud_run_v2_service.fastapi_backend.uri
      }
      env {
        # UISettings requires this too - it's the UI's own login gate, checked
        # before any request reaches the backend's separate APP_PASSWORD check.
        name  = "APP_PASSWORD"
        value = var.app_password
      }

      ports {
        container_port = 8080
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = google_cloud_run_v2_service.gradio_frontend.project
  location = google_cloud_run_v2_service.gradio_frontend.location
  name     = google_cloud_run_v2_service.gradio_frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "frontend_url" {
  description = "public frontend url"
  value       = google_cloud_run_v2_service.gradio_frontend.uri
}
