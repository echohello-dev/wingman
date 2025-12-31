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

output "client_id" {
  description = "Slack App Client ID"
  value       = slackapp_application.wingman.credentials.client_id
  sensitive   = true
}

output "client_secret" {
  description = "Slack App Client Secret"
  value       = slackapp_application.wingman.credentials.client_secret
  sensitive   = true
}

output "signing_secret" {
  description = "Slack App Signing Secret"
  value       = slackapp_application.wingman.credentials.signing_secret
  sensitive   = true
}

output "verification_token" {
  description = "Slack App Verification Token"
  value       = slackapp_application.wingman.credentials.verification_token
  sensitive   = true
}

