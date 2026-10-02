# Write-capable deploy identity for Cloud Run — distinct from terraform/ci/'s
# read-only plan-review service account. Reuses that module's Workload
# Identity Federation pool/provider (a cross-state reference via data
# sources, not a remote-state read) but with a tighter binding: scoped to
# attribute.ref == refs/heads/master, not just the repository, since this
# identity can actually build, migrate, and deploy production — unlike the
# plan-only SA, which only ever needs read access from any branch.

data "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-actions"
}

data "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = data.google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
}

resource "google_service_account" "cd" {
  account_id   = "linguaalayam-cd"
  display_name = "linguaalayam CD — build, migrate, deploy to Cloud Run"
}

resource "google_service_account_iam_member" "cd_wif_binding" {
  service_account_id = google_service_account.cd.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${data.google_iam_workload_identity_pool.github.name}/attribute.ref/refs/heads/master"
}

resource "google_artifact_registry_repository_iam_member" "cd_registry_writer" {
  location   = google_artifact_registry_repository.linguaalayam.location
  repository = google_artifact_registry_repository.linguaalayam.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.cd.email}"
}

# roles/run.developer (not the broader roles/run.admin) — covers deploying a
# new revision and executing jobs, not setting IAM policy on Cloud Run
# resources, which this identity never needs.
resource "google_cloud_run_v2_service_iam_member" "cd_service_developer" {
  name     = google_cloud_run_v2_service.linguaalayam.name
  location = var.region
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.cd.email}"
}

resource "google_cloud_run_v2_job_iam_member" "cd_migrate_developer" {
  name     = google_cloud_run_v2_job.linguaalayam_migrate.name
  location = var.region
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.cd.email}"
}

# Deploying a revision that runs *as* cloud_run_sa requires this — without
# it, a deploy attempt fails with "iam.serviceaccounts.actAs" denied.
resource "google_service_account_iam_member" "cd_act_as_runtime_sa" {
  service_account_id = google_service_account.cloud_run_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cd.email}"
}

# One-off migration runner — same image/env/secrets as the live service, but
# overrides the container command to run Alembic instead of starting the API
# server. Executed once per deploy by the CD workflow, before the service
# itself is updated, replacing the manual SSH-tunnel migration this session
# relied on.
resource "google_cloud_run_v2_job" "linguaalayam_migrate" {
  name     = "linguaalayam-migrate"
  location = var.region

  template {
    template {
      service_account = google_service_account.cloud_run_sa.email

      # Same Direct VPC egress path as the main service — the migration job
      # must also leave through Cloud NAT's static IP, the only address
      # Hetzner's firewall allow-lists on port 5432 (see networking.tf).
      vpc_access {
        network_interfaces {
          network    = google_compute_network.linguaalayam.id
          subnetwork = google_compute_subnetwork.linguaalayam.id
        }
        egress = "ALL_TRAFFIC"
      }

      containers {
        image   = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.linguaalayam.repository_id}/linguaalayam:${var.image_tag}"
        command = ["python", "-m", "alembic", "upgrade", "head"]

        env {
          name  = "DB_HOST"
          value = var.db_host
        }
        env {
          name  = "DB_PORT"
          value = var.db_port
        }
        env {
          name  = "DB_NAME"
          value = var.db_name
        }
        env {
          name  = "DB_USER"
          value = var.db_user
        }
        # No DB_SSLMODE here: unlike api/app.py (which never actually reads
        # it — confirmed working all session despite the service having
        # this same var set), Alembic's env.py goes through the Hydra-based
        # config path, which does act on it, and Hetzner's Postgres doesn't
        # support SSL at all. Setting it broke this job's first real run.
        env {
          name = "DB_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_password.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}
