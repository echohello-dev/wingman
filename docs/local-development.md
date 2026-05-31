# Local Development Guide

Run Wingman bot locally with live streaming support.

## Prerequisites

- Python 3.11+ (for local bot development)
- Docker & Docker Compose (for services)
- Slack workspace with admin access
- OpenRouter or OpenAI API key

## 1. Get Slack App Credentials

### Option A: Use Existing App

If you already have a Slack app:
1. Go to [api.slack.com/apps](https://api.slack.com/apps) → select your app
2. Get **Bot Token**: OAuth & Permissions → Bot User OAuth Token (xoxb-...)
3. Get **App Token**: Basic Information → App-Level Tokens → Generate (xapp-...)
4. Get **Signing Secret**: Basic Information → Signing Secret

### Option B: Create New App

```bash
# 1. Go to https://api.slack.com/apps and create a new app
# 2. Name it "Wingman-dev" for local testing
```

**Required Scopes** (OAuth & Permissions):
```
app_mentions:read
channels:history
channels:read
chat:write
im:history
im:read
im:write
users:read
```

**Enable Socket Mode** (Basic Information):
- Toggle Socket Mode ON
- Generate App-Level Token with `connections:write` scope

**Enable Events** (Event Subscriptions):
- Toggle ON
- Subscribe to: `app_mention`, `message.im`

## 2. Environment Setup

```bash
cd wingman
cp .env.example .env
```

Edit `.env`:
```bash
# Required Slack Tokens
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret

# AI Provider (choose one)
OPENROUTER_API_KEY=sk-or-your-key
# OR
OPENAI_API_KEY=sk-your-key

# Model
LLM_MODEL=openai/gpt-4-turbo-preview
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

## 3. Start Supporting Services

```bash
docker compose up -d postgres chroma
```

Verify:
```bash
docker compose ps
```

## 4. Run Bot Locally

### Using mise (recommended)

```bash
mise run dev-bot
```

### Or directly

```bash
cd backend
uv sync
python run_bot.py
```

### Verify Bot is Running

```bash
# Check logs
docker compose logs -f bot

# Or if running directly, you should see:
# INFO:slack_bolt.adapter.socket_mode.base_socket_mode:Starting Socket Mode handler...
```

## 5. Test in Slack

### DM the Bot
- Open Slack DM to @Wingman
- Send: `Hello!`
- You should see streaming thinking steps appear

### Mention in Channel
- Invite bot: `/invite @Wingman`
- Post: `@Wingman what's the status?`
- Watch the streaming response

### Use Slash Command
- Type: `/wingman hello`

## 6. Streaming Behavior

When streaming is working, you should see:

```
🧠 Processing your request...
  ✅ Analyzing question...
  🔍 Searching knowledge base...
  ✅ Searching knowledge base...
  ✍️ Generating response...
  ✅ Generating response...

[Full answer appears here]
```

The thinking steps show the bot's reasoning process in real-time.

## Troubleshooting

### Bot Not Responding

```bash
# Check bot logs
docker compose logs -f bot

# Common fixes:
# 1. Verify SLACK_BOT_TOKEN starts with xoxb-
# 2. Verify SLACK_APP_TOKEN starts with xapp-
# 3. Verify Socket Mode is enabled in Slack app settings
# 4. Verify Event Subscriptions are configured
```

### Streaming Not Working

1. Verify slack-sdk version is 3.40.0+:
   ```bash
   pip show slack-sdk | grep Version
   ```

2. Check streaming is enabled in your Slack app:
   - App settings → Socket Mode → should be ON
   - App settings → Event Subscriptions → should be ON

3. Test with a simple message first

### Database Errors

```bash
# Reset database
docker compose down -v
docker compose up -d postgres chroma
```

### Port Conflicts

If ports 5432 or 8001 are in use:
```bash
# Edit docker-compose.yaml to change ports
```

## Mise Commands Reference

Wingman uses [mise](https://mise.jdx.dev/) for task management. All tasks are defined in `mise.toml`.

### Docker Services

```bash
mise run up              # Start all services
mise run down            # Stop all services
mise run restart         # Restart all services
mise run ps              # Show running services
mise run logs            # Tail all logs
mise run logs-bot        # Tail bot logs
mise run logs-backend    # Tail backend logs
mise run logs-frontend   # Tail frontend logs
mise run clean           # Remove containers and volumes
```

### Local Development

```bash
mise run dev-backend     # Run backend API locally (port 8000)
mise run dev-bot         # Run bot locally (with streaming)
mise run dev-frontend    # Run frontend locally (port 3000)
```

### Dependencies

```bash
mise run install         # Install all dependencies
mise run install-backend # Install backend deps (uv sync)
mise run install-frontend # Install frontend deps (bun install)
```

### Database

```bash
mise run migrate              # Run pending migrations
mise run migrate-down         # Rollback last migration
mise run migrate-create       # Create new migration (set MIGRATION_MESSAGE=...)
mise run migrate-history      # Show migration history
mise run migrate-current      # Show current version
mise run shell-db             # Open PostgreSQL shell
```

### Testing

```bash
mise run test             # Run all tests
mise run test-backend     # Run backend tests
mise run test-frontend    # Run frontend tests
```

### Terraform (Slack App IaC)

```bash
mise run tf-init              # Initialize Terraform
mise run tf-plan              # Plan changes
mise run tf-apply             # Apply changes (creates Slack app)
mise run tf-destroy            # Destroy resources
mise run tf-output             # Show outputs
mise run tf-credentials       # Show Slack credentials (sensitive!)
mise run tf-sync-vars          # Sync .env → Terraform Cloud
mise run tf-load-vars         # Load Terraform Cloud → .env
mise run tf-oauth-url         # Show OAuth install URL
```

### Full List

```bash
mise tasks
```

## Development Workflow

### Run All Services

```bash
# Terminal 1: Backend API
mise run dev-backend

# Terminal 2: Bot (with streaming)
mise run dev-bot

# Terminal 3: Frontend
mise run dev-frontend
```

### Rebuild After Changes

```bash
# For Docker deployment
docker compose up -d --build bot

# For local
cd backend && uv sync
```

## Next Steps

- [Full Setup Guide](setup.md) - Complete deployment instructions
- [Slack Auth Reference](slack-auth.md) - Token details and security
- [Getting Started](getting-started.md) - Quick start overview
