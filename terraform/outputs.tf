output "cloud_run_url" {
  description = "The URL of the deployed FitForge AI Cloud Run service"
  value       = google_cloud_run_v2_service.fitforge_service.uri
}

output "artifact_registry_repo" {
  description = "The Artifact Registry Docker repository name"
  value       = google_artifact_registry_repository.fitforge_repo.name
}

output "service_account_email" {
  description = "The Service Account email used by Cloud Run"
  value       = google_service_account.fitforge_runner.email
}

output "secret_manager_secret_id" {
  description = "The Secret Manager secret ID for GEMINI_API_KEY"
  value       = google_secret_manager_secret.gemini_api_key.secret_id
}
