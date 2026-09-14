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
}

variable "admin_user" {
  description = "HTTP Basic Auth username for /admin/analytics"
  type        = string
  default     = "admin"
}

# Sensitive values — supplied via terraform.tfvars (gitignored) or -var on the CLI,
# never committed. Stored into Secret Manager below, not passed to Cloud Run as
# plain env vars.
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
