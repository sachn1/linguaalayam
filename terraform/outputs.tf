output "service_url" {
  value = google_cloud_run_v2_service.linguaalayam.uri
}

output "artifact_registry_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.linguaalayam.repository_id}"
}

output "nat_static_ip" {
  description = "The one IP Cloud Run's outbound traffic now originates from — allow-list this on Hetzner's firewall for Postgres."
  value       = google_compute_address.nat_ip.address
}
