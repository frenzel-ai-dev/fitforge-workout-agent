# Terraform configuration for FitForge AI Google Cloud Infrastructure

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required GCP APIs
resource "google_project_service" "required_services" {
  for_each = toset([
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com"
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# 2. Artifact Registry for Container Images
resource "google_artifact_registry_repository" "fitforge_repo" {
  location      = var.region
  repository_id = "fitforge-repo"
  description   = "Docker repository for FitForge AI agent images"
  format        = "DOCKER"
  depends_on    = [google_project_service.required_services]
}

# 3. Secret Manager for Gemini API Key
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "GEMINI_API_KEY"
  replication {
    auto {}
  }
  depends_on = [google_project_service.required_services]
}

# 4. Service Account for FitForge Cloud Run
resource "google_service_account" "fitforge_runner" {
  account_id   = "fitforge-runner-sa"
  display_name = "FitForge AI Cloud Run Service Account"
}

# 5. IAM Roles for Service Account
resource "google_project_iam_member" "aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.fitforge_runner.email}"
}

resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.fitforge_runner.email}"
}

# 6. Cloud Run Service Deployment
resource "google_cloud_run_v2_service" "fitforge_service" {
  name     = "fitforge-agent"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.fitforge_runner.email
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/fitforge-repo/fitforge-agent:latest"
      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      ports {
        container_port = 8501
      }
    }
  }

  depends_on = [
    google_project_service.required_services,
    google_artifact_registry_repository.fitforge_repo
  ]
}

# 7. Allow Public Unauthenticated Access (Optional / Configurable)
resource "google_cloud_run_service_iam_member" "public_access" {
  count    = var.allow_public_access ? 1 : 0
  location = google_cloud_run_v2_service.fitforge_service.location
  project  = google_cloud_run_v2_service.fitforge_service.project
  service  = google_cloud_run_v2_service.fitforge_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
