resource "google_artifact_registry_repository" "linguaalayam" {
  repository_id = "linguaalayam"
  location      = var.region
  format        = "DOCKER"
  description   = "linguaalayam app images"
}

resource "google_service_account" "cloud_run_sa" {
  account_id   = "linguaalayam-run"
  display_name = "linguaalayam Cloud Run runtime SA"
}

resource "google_secret_manager_secret_iam_member" "db_password_access" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "together_key_access" {
  secret_id = google_secret_manager_secret.together_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "admin_password_access" {
  secret_id = google_secret_manager_secret.admin_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_cloud_run_v2_service" "linguaalayam" {
  name                = "linguaalayam"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.linguaalayam.id
        subnetwork = google_compute_subnetwork.linguaalayam.id
      }
      egress = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.linguaalayam.repository_id}/linguaalayam:${var.image_tag}"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
        cpu_idle          = true # CPU only allocated while handling a request
        startup_cpu_boost = true # extra CPU during startup only — cuts cold start
        # without paying for a warm min-instance
      }

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
      env {
        name  = "DB_SSLMODE"
        value = "require"
      }
      env {
        name  = "MCP_ISSUER_URL"
        value = var.mcp_issuer_url
      }
      env {
        name  = "ADMIN_USER"
        value = var.admin_user
      }

      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "TOGETHER_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.together_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "ADMIN_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.admin_password.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# MCP server + admin dashboard need to be publicly reachable (OAuth discovery,
# MCP_ISSUER_URL). /admin/analytics is protected by its own HTTP Basic Auth,
# so public invoker is fine here.
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  name     = google_cloud_run_v2_service.linguaalayam.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Custom domains for the Cloud Run service. Created by hand during the DNS
# cutover (`gcloud beta run domain-mappings create`) before this config
# existed — imported into state rather than left as untracked infra.
# DNS itself (A/AAAA records for the apex, CNAME for www, both DNS-only/grey
# cloud in Cloudflare — not proxied, since Google's managed TLS cert
# issuance needs to see the domain directly) lives outside Terraform, in
# Cloudflare.
resource "google_cloud_run_domain_mapping" "linguaalayam_org" {
  location = var.region
  name     = "linguaalayam.org"

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_v2_service.linguaalayam.name
  }

  # certificate_mode is unset (null) on the live resource, created via
  # `gcloud beta run domain-mappings create` before this config existed.
  # Leaving it out of spec{} makes the provider inject "AUTOMATIC" as a
  # plan-time default — and it's a ForceNew field, so that default alone
  # would destroy and recreate this already-live, cert-provisioned,
  # traffic-serving mapping for no functional change. Ignored deliberately.
  lifecycle {
    ignore_changes = [spec[0].certificate_mode]
  }
}

resource "google_cloud_run_domain_mapping" "www_linguaalayam_org" {
  location = var.region
  name     = "www.linguaalayam.org"

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_v2_service.linguaalayam.name
  }

  # See linguaalayam_org above — same reason.
  lifecycle {
    ignore_changes = [spec[0].certificate_mode]
  }
}
