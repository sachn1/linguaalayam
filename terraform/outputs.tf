output "service_url" {
  value = google_cloud_run_v2_service.linguaalayam.uri
}

output "artifact_registry_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.linguaalayam.repository_id}"
}
