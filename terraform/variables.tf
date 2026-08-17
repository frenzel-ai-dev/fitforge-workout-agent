variable "project_id" {
  description = "The Google Cloud project ID to deploy FitForge AI resources"
  type        = string
}

variable "region" {
  description = "The GCP region for Cloud Run and Artifact Registry"
  type        = string
  default     = "us-central1"
}

variable "allow_public_access" {
  description = "Whether to allow unauthenticated access to the Streamlit UI"
  type        = bool
  default     = true
}
