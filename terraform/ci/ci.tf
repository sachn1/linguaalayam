# Read-only identity for GitHub Actions to run `terraform plan` against the
# application infra in ../ (a separate state — see README.md in this
# directory for why) and post the result as a PR comment. Deliberately
# cannot apply: no long-lived key ever leaves GCP (Workload Identity
# Federation exchanges GitHub's own OIDC token for short-lived credentials
# per run), and the service account only ever gets viewer-level roles.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-actions"
  display_name              = "GitHub Actions"
  description               = "Federated identities for GitHub Actions workflows"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # Only OIDC tokens minted for this exact repo's workflows can use this
  # provider — a token from any other GitHub repo is rejected outright.
  attribute_condition = "assertion.repository == '${var.github_repository}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "ci_plan" {
  account_id   = "linguaalayam-ci-plan"
  display_name = "linguaalayam CI — terraform plan (read-only)"
}

# roles/viewer covers read access across the resource types the application
# module manages (Compute/VPC/NAT, Cloud Run, Artifact Registry, IAM) —
# broad but strictly read-only, appropriate for an identity that only ever
# computes a plan and never applies one.
resource "google_project_iam_member" "ci_plan_viewer" {
  project = var.project_id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.ci_plan.email}"
}

# roles/viewer doesn't cover Secret Manager — needed so `plan` can see that
# the secret resources exist (never their values; that needs secretAccessor,
# which this service account deliberately never gets).
resource "google_project_iam_member" "ci_plan_secrets_viewer" {
  project = var.project_id
  role    = "roles/secretmanager.viewer"
  member  = "serviceAccount:${google_service_account.ci_plan.email}"
}

resource "google_service_account_iam_member" "ci_plan_wif_binding" {
  service_account_id = google_service_account.ci_plan.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}
