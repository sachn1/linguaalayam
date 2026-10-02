output "ci_workload_identity_provider" {
  description = "Paste into the GCP_WIF_PROVIDER GitHub Actions secret."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "ci_service_account_email" {
  description = "Paste into the GCP_CI_PLAN_SA GitHub Actions secret."
  value       = google_service_account.ci_plan.email
}
