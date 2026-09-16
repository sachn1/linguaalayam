variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "linguaalayam"
}

variable "region" {
  description = "GCP region — provider default only, none of this module's resources are regional"
  type        = string
  default     = "europe-west1"
}

variable "github_repository" {
  description = "GitHub \"owner/repo\" allowed to assume the CI service account via Workload Identity Federation"
  type        = string
  default     = "sachn1/linguaalayam"
}
