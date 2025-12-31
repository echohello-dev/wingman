variable "app_name" {
  description = "Name of the Slack app"
  type        = string
  default     = "Wingman"
}

variable "app_description" {
  description = "Short description of the Slack app"
  type        = string
  default     = "AI-powered Slack support assistant with RAG capabilities"
}

variable "app_long_description" {
  description = "Long description of the Slack app"
  type        = string
  default     = <<-EOT
    Wingman is an intelligent support assistant that uses Retrieval-Augmented Generation (RAG) 
    to provide accurate, context-aware responses to your questions. It learns from your 
    documentation and Slack conversations to deliver helpful answers directly in Slack.
  EOT
}

variable "app_background_color" {
  description = "Background color for the Slack app (hex format)"
  type        = string
  default     = "#4A154B"
}

variable "bot_display_name" {
  description = "Display name for the bot user"
  type        = string
  default     = "Wingman"
}

variable "socket_mode_enabled" {
  description = "Enable Socket Mode for real-time events (recommended for development)"
  type        = bool
  default     = true
}
