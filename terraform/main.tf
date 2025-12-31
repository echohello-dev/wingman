terraform {
  required_version = ">= 1.0"

  required_providers {
    slackapp = {
      source  = "yumemi-inc/slackapp"
      version = "~> 0.2.7"
    }
  }
}

provider "slackapp" {
  # Configured via environment variables:
  # - SLACK_APP_CONFIGURATION_TOKEN
  # - SLACK_REFRESH_TOKEN
}

data "slackapp_manifest" "wingman" {
  display_information {
    name             = var.app_name
    description      = var.app_description
    background_color = var.app_background_color
    long_description = var.app_long_description
  }

  features {
    app_home {
      home_tab_enabled             = false
      messages_tab_enabled         = true
      messages_tab_read_only_enabled = false
    }

    bot_user {
      display_name  = var.bot_display_name
      always_online = true
    }

    slash_command {
      command      = "/wingman"
      description  = "Ask Wingman a question"
      usage_hint   = "[your question]"
      should_escape = false
    }
  }

  oauth_config {
    scopes {
      bot = [
        "app_mentions:read",
        "channels:history",
        "channels:read",
        "chat:write",
        "im:history",
        "im:read",
        "im:write",
        "reactions:read",
        "users:read",
        "commands",
      ]
    }
  }

  settings {
    org_deploy_enabled     = false
    socket_mode_enabled    = var.socket_mode_enabled
    token_rotation_enabled = false

    event_subscriptions {
      bot_events = [
        "app_mention",
        "message.im",
        "reaction_added",
      ]
    }

    interactivity {
      is_enabled = true
    }
  }
}

resource "slackapp_application" "wingman" {
  manifest = data.slackapp_manifest.wingman.json
}
