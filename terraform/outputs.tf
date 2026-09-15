output "service_url" {
  description = "Public URL of the Cloud Run service"
  value       = google_cloud_run_service.mcp_service.status[0].url
}