variable "project_id" {
  description = "gcp project id"
  type        = string
}

variable "backend_image" {
  description = "Fully qualified image tag for the FastAPI backend (e.g. from Artifact Registry)"
  type        = string
}

variable "frontend_image" {
  description = "Fully qualified image tag for the Gradio frontend (e.g. from Artifact Registry)"
  type        = string
}

variable "hf_api_key" {
  description = "Hugging Face access token for the FastAPI backend's Settings - downloads the model at startup (required, no default)"
  type        = string
  sensitive   = true
}

variable "hf_model_repo_id" {
  description = "HF Hub repo id the backend downloads the model from, for the FastAPI backend's Settings (required, no default)"
  type        = string
}

variable "app_password" {
  description = "Shared password gate, required by both the FastAPI backend's Settings and the Gradio frontend's UISettings (required, no default)"
  type        = string
  sensitive   = true
}
