# Terraform Guide for Wingman

This guide explains how to manage Wingman's Slack app infrastructure using Terraform.

## Overview

Wingman uses Infrastructure as Code (IaC) via Terraform to automatically create and manage the Slack app. This eliminates manual configuration and enables reproducible deployments.

**Key Benefits:**
- Automated Slack app creation with correct scopes and permissions
- Token rotation management
- Version-controlled infrastructure configuration
- Reproducible deployments across environments

**Terraform Cloud (Optional):**
Terraform Cloud provides remote state storage and collaboration features, but it's **not required**. You can use local state or any other [Terraform backend](https://www.terraform.io/language/settings/backends). Terraform Cloud is convenient for teams because it provides:
- Encrypted remote state storage
- Token rotation management via workspace variables
- Access control and audit logs
- State locking to prevent concurrent modifications

For local development or personal use, you can skip Terraform Cloud and use local state.

## Prerequisites

- Terraform 1.12+ (managed by mise)
- `uv` for Python dependency management
- Slack workspace admin access
- (Optional) Terraform Cloud account for remote state - [free tier available](https://app.terraform.io/)

## Quick Start

### Option A: With Terraform Cloud (Recommended for Teams)

#### 1. Initialize Terraform Cloud

Sign up for [Terraform Cloud](https://app.terraform.io/) (free tier available).

Create an organization and workspace, or use the defaults during setup:
```bash
TF_CLOUD_ORGANIZATION=your-org
TF_WORKSPACE=wingman
```

Generate a Terraform Cloud API token from [https://app.terraform.io/app/settings/tokens](https://app.terraform.io/app/settings/tokens).

#### 2. Setup Environment Variables

Add to `.env`:
```bash
# Terraform Cloud
TF_CLOUD_ORGANIZATION=your-org
TF_WORKSPACE=wingman
TF_TOKEN_app_terraform_io=your-terraform-cloud-token

# Slack (obtained from initial app setup or token rotation)
SLACK_CONFIG_ACCESS_TOKEN=xoxe.xoxp-1-...
SLACK_CONFIG_REFRESH_TOKEN=xoxe-1-...
```

Mise automatically loads `.env` for all tasks via `[env]` configuration in `mise.toml`.

### 3. Deploy Slack App

```bash
# Initialize Terraform (downloads provider and sets up state)
mise run tf-init

# Review what will be created
mise run tf-plan

# Create the Slack app
mise run tf-apply
```

The Terraform output will show:
- **App ID** (A0A71KHRFNU)
- **OAuth authorize URL** for installation
- **App credentials** (signing secret, client ID, etc.)

### 4. Load Slack Credentials from Terraform

After applying Terraform, load the generated credentials into `.env`:

```bash
mise run tf-load-vars
```

This loads:
- `SLACK_CLIENT_ID`
- `SLACK_CLIENT_SECRET`
- `SLACK_SIGNING_SECRET`
- `SLACK_VERIFICATION_TOKEN`

### 5. Install App to Workspace and Get Bot Tokens

```bash
# Get the OAuth installation URL
mise run tf-output | grep oauth_authorize_url
```

Visit the URL and click "Install to Workspace". This will prompt you to:
1. Select the workspace to install the app
2. Review requested permissions (scopes)
3. Click "Allow"

After installation, Slack will show your app's tokens:

**Copy these tokens and add to `.env`:**

```bash
# Navigate to your Slack app at https://api.slack.com/apps
# Select your app (Wingman)
# Go to "OAuth & Permissions" section

SLACK_BOT_TOKEN=xoxb-...        # Bot User OAuth Token
SLACK_APP_TOKEN=xapp-...        # App-Level Token (for Socket Mode)
```

**To find these tokens:**
1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Select your Wingman app
3. **OAuth & Permissions** → Copy "Bot User OAuth Token" (xoxb-...)
4. **Socket Mode** → Copy "App-Level Token" (xapp-...)
5. Paste both into `.env`

### 6. (Optional) Load All Credentials from Terraform State

To load all credentials (except bot/app tokens which require manual installation):

```bash
mise run tf-load-vars
```

**Note:** `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` are NOT available from Terraform outputs because they are only generated after you install the app to your workspace. These must be manually copied from Slack after installation.

### 4. Install App to Workspace

```bash
# Get the OAuth URL
mise run tf-output

# Or just the authorize URL
mise run tf-output | grep oauth_authorize_url
```

Visit the URL and click "Install to Workspace". This generates:
- **Bot token** (xoxb-...) - for the bot to act
- **App token** (xapp-...) - for Socket Mode

Copy these to `.env`:
```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

### 5. Load Signing Secret

```bash
mise run tf-load-credentials
```

This extracts the signing secret from Terraform and adds it to `.env`.

## Common Tasks

### View Terraform State

```bash
# Show all outputs
mise run tf-output

# Show specific output
mise run tf-output -json app_id

# View app credentials (sensitive data)
mise run tf-credentials
```

### Rotate and Load Tokens

Slack tokens expire after 12 hours. Rotate them before expiry:

```bash
# Sync (rotate) tokens TO Terraform Cloud from .env
mise run tf-sync-vars

# Load credentials FROM Terraform outputs to .env
mise run tf-load-vars
```

**Token Lifecycle:**

1. **`tf-sync-vars`** - Updates Terraform Cloud with fresh tokens from `.env`
   - Validates tokens from `.env`
   - Falls back to Terraform Cloud if `.env` tokens invalid
   - Rotates tokens via Slack API
   - Updates `.env` and Terraform Cloud workspace variables

2. **`tf-load-vars`** - Loads Slack credentials from Terraform outputs to `.env`
   - Extracts `signing_secret`, `client_id`, `client_secret`, `verification_token`
   - Updates existing values in `.env`
   - **Note:** `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` must be manually added after installing the app to your workspace

### Rotate Tokens

Slack tokens expire after 12 hours. Rotate them before expiry:

```bash
mise run tf-sync-vars
```

This script:
1. Validates tokens from `.env` by attempting rotation
2. Falls back to Terraform Cloud if `.env` tokens invalid
3. If both invalid, prompts for manual token entry with link to Slack API
4. Rotates tokens via Slack's `tooling.tokens.rotate` API
5. Updates local `.env` file
6. Syncs new tokens to Terraform Cloud workspace variables

### Plan Changes

Before applying, always review what Terraform will change:

```bash
mise run tf-plan
```

### Update Slack App Configuration

Edit `terraform/variables.tf` to customize:

```hcl
variable "app_name" {
  default = "Wingman"
}

variable "app_description" {
  default = "AI-powered Slack support assistant"
}

variable "bot_display_name" {
  default = "Wingman"
}

variable "socket_mode_enabled" {
  default = true
}
```

Then apply:

```bash
mise run tf-plan
mise run tf-apply
```

### Destroy Slack App

```bash
mise run tf-destroy
```

This removes the Slack app from your workspace. Requires confirmation.

## Architecture

### Terraform Files

- **`terraform/main.tf`** - Slack app provider and resource
  - Configures Slack provider with tokens
  - Creates app from manifest
  
- **`terraform/variables.tf`** - Input variables
  - App name, description, colors
  - Display settings
  
- **`terraform/outputs.tf`** - Output values
  - App ID for reference
  - OAuth URL for installation
  - App credentials (signing secret, etc.)
  
- **`terraform/backend.tf`** - Remote state configuration
  - Uses Terraform Cloud backend
  - Reads from environment variables (not hardcoded)

### Scripts

- **`scripts/sync_tf_vars.py`** - Token management
  - Validates and rotates Slack tokens
  - Updates `.env` and Terraform Cloud
  - Handles invalid tokens with user prompts

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `TF_CLOUD_ORGANIZATION` | Terraform Cloud org | your-org |
| `TF_WORKSPACE` | Terraform Cloud workspace | wingman |
| `TF_TOKEN_app_terraform_io` | Terraform Cloud API token | tfp_xxxx... |
| `SLACK_CONFIG_ACCESS_TOKEN` | Slack API token | xoxe.xoxp-1-... |
| `SLACK_CONFIG_REFRESH_TOKEN` | Slack refresh token | xoxe-1-... |

## Troubleshooting

### "TF_CLOUD_ORGANIZATION not set"

Ensure `.env` is properly configured:
```bash
cp .env.example .env
# Edit .env with your values
mise run tf-init
```

### "invalid_refresh_token" error

Tokens may have expired. Rotate them:
```bash
mise run tf-sync-vars
```

If `tf-sync-vars` prompts for manual entry:
1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Select your app
3. Navigate to "Tokens and installation"
4. Copy "Refresh token for rotation" (xoxe-1-...)
5. Paste when prompted

### State mismatch between local and Terraform Cloud

Ensure environment variables match what's in Terraform Cloud:
```bash
# Check local state
mise run tf-plan

# If differences appear, verify tokens are synced
mise run tf-sync-vars

# Then re-plan
mise run tf-plan
```

### Can't find Terraform Cloud workspace

Verify the workspace exists:
1. Log in to [https://app.terraform.io](https://app.terraform.io)
2. Navigate to your organization
3. Check the workspace name matches `TF_WORKSPACE` in `.env`

### "Backend initialization required"

Re-initialize Terraform:
```bash
cd terraform
rm -rf .terraform .terraform.lock.hcl
cd ..
mise run tf-init
```

## Security

### Token Safety

- **Never commit tokens to git** - they're in `.env` which is `.gitignore`d
- **Rotate tokens regularly** - use `mise run tf-sync-vars` before 12h expiry
- **Use Terraform Cloud variables** - sensitive data is encrypted at rest
- **Limit permissions** - Slack tokens should have minimal required scopes

### Backend Security

Terraform Cloud provides:
- Encrypted state storage
- Access control (team/org level)
- Audit logs
- State locking to prevent concurrent modifications

## Advanced Usage

### Multiple Workspaces (Teams)

Create separate Terraform Cloud workspaces for dev/staging/prod:

```bash
# For dev environment
TF_WORKSPACE=wingman-dev mise run tf-init

# For prod environment
TF_WORKSPACE=wingman-prod mise run tf-init
```

### Customize Slack App

Edit `terraform/variables.tf`:

```hcl
variable "app_background_color" {
  default = "#36c5f0"  # Slack blue
}

variable "slash_commands" {
  type = list(string)
  default = ["/wingman", "/help"]
}
```

Update `terraform/main.tf` to use these variables in the manifest.

### View Drift Detection

Check if your Slack app configuration has drifted from Terraform:

```bash
mise run tf-plan
```

Any changes will be shown. To sync to Terraform state:

```bash
mise run tf-apply
```

## Related Documentation

- [Slack API Documentation](https://api.slack.com/)
- [Terraform Cloud Documentation](https://www.terraform.io/cloud/docs)
- [terraform-provider-slackapp](https://github.com/yumemi-inc/terraform-provider-slackapp)
- [Setup Guide](./setup.md) - General project setup
- [Slack Authentication](./slack-auth.md) - Token types and permissions
