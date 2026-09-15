variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Region for Cloud Run"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "agentsmcp"
}

variable "container_image" {
  description = "Full container image reference (including tag) – e.g. us-docker.pkg.dev/<project>/<repo>/image:tag"
  type        = string
}