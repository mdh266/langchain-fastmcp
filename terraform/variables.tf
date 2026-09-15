variable "project_id" {
  description = "GCP project ID"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "Region for Cloud Run"
  type        = string
  default     = "us-central1"
  sensitive   = false
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "agentsmcp"
  sensitive   = false
}

variable "container_image" {
  description = "Full container image reference (including tag) – e.g. us-docker.pkg.dev/<project>/<repo>/image:tag"
  type        = string
  sensitive   = false
}