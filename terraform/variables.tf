variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "linguaalayam"
}

variable "region" {
  description = "GCP region for Artifact Registry and Cloud Run"
  type        = string
  default     = "europe-west1"
}

variable "image_tag" {
  description = "Tag of the linguaalayam image to deploy (pushed to Artifact Registry by CI)"
  type        = string
  default     = "latest"
}

variable "db_host" {
  description = "Hetzner Postgres host, reachable from Cloud Run's public egress"
  type        = string

  # Hetzner's origin IP, not the linguaalayam.org hostname. That domain is
  # proxied through Cloudflare (resolves to a Cloudflare IP, confirmed via
  # `getent hosts`), and Cloudflare's standard proxy only forwards HTTP(S),
  # not arbitrary TCP like Postgres on 5432. Cloudflare Spectrum *can* proxy
  # arbitrary TCP/UDP ports, and would be the ideal way to keep this off a
  # bare IP — but it's a paid add-on, likely costing more on its own than
  # this whole Cloud NAT setup, and it would widen Hetzner's firewall rule
  # from our one known Cloud NAT static IP to Cloudflare's entire published
  # IP range. Not worth it for a single known caller.
  default = "178.105.165.149"
}

variable "db_port" {
  type    = string
  default = "5432"
}

variable "db_name" {
  type    = string
  default = "linguaalayam"
}

variable "db_user" {
  type    = string
  default = "postgres"
}

variable "mcp_issuer_url" {
  description = "Public URL where /mcp is reachable, e.g. https://linguaalayam.org/mcp"
  type        = string
  default     = "https://linguaalayam.org/mcp"
}

variable "admin_user" {
  description = "HTTP Basic Auth username for /admin/analytics"
  type        = string
  default     = "admin"
}

# Sensitive values — the only variables with no default, so `terraform plan`/
# `apply` always prompts for them (or reads TF_VAR_* env vars) rather than
# risk silently reusing a stale or wrong secret. Never put these in
# terraform.tfvars or any committed file. Stored into Secret Manager below,
# not passed to Cloud Run as plain env vars.
variable "db_password" {
  type      = string
  sensitive = true
}

variable "together_api_key" {
  description = "TogetherAI key for the server-side default LLM (Qwen 3.5 9B) used when a user enables AI synthesis without supplying their own key"
  type        = string
  sensitive   = true
}

variable "admin_password" {
  type      = string
  sensitive = true
}
