# Small bucket for build-time assets that are deliberately not committed to
# git — currently just the MaxMind GeoLite2-City database (~64MB, a
# third-party download, gitignored under data/**). The Dockerfile bakes it
# into the image via a plain COPY, which only works when the file actually
# exists in the build context — true on a local machine, never true for a
# fresh CI checkout. The CD workflow downloads it from here immediately
# before building. See .env.example for how to (re)obtain the file from
# MaxMind if it ever needs refreshing or re-uploading.
resource "google_storage_bucket" "assets" {
  name                        = "${var.project_id}-assets"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
}

resource "google_storage_bucket_iam_member" "cd_assets_reader" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.cd.email}"
}
