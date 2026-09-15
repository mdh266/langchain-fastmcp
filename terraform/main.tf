terraform {
  required_version = ">=1.15.3"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~>5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_cloud_run_service" "mcp_service" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = var.container_image

        resources {
          limits = {
            cpu    = "1"
            memory = "256Mi"
          }
        }
      }
    }
  }
}

resource "google_cloud_run_service_iam_member" "public_invoker" {
  location = google_cloud_run_service.mcp_service.location
  project  = var.project_id
  service  = google_cloud_run_service.mcp_service.name

  role   = "roles/run.invoker"
  member = "allUsers"
}