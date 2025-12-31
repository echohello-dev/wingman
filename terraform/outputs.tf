output "app_id" {
  description = "The Slack App ID"
  value       = slackapp_application.wingman.id
}

output "oauth_authorize_url" {
  description = "OAuth authorization URL - visit this to install the app"
  value       = slackapp_application.wingman.oauth_authorize_url
}

output "app_credentials" {
  description = "OAuth credentials (client_id, client_secret, signing_secret, verification_token)"
  value       = slackapp_application.wingman.credentials
  sensitive   = true
}
