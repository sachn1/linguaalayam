# Secret Manager holds the values Cloud Run shouldn't see as plain env vars.
# Each secret needs the Cloud Run runtime service account granted accessor —
# see the IAM binding in cloud_run.tf.

resource "google_secret_manager_secret" "db_password" {
  secret_id = "linguaalayam-db-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

resource "google_secret_manager_secret" "together_api_key" {
  secret_id = "linguaalayam-together-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "together_api_key" {
  secret      = google_secret_manager_secret.together_api_key.id
  secret_data = var.together_api_key
}

resource "google_secret_manager_secret" "admin_password" {
  secret_id = "linguaalayam-admin-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "admin_password" {
  secret      = google_secret_manager_secret.admin_password.id
  secret_data = var.admin_password
}
