# Quick Start Guide

Get Wingman running in minutes with AI streaming support.

## Prerequisites

- Docker and Docker Compose
- Slack workspace admin access
- OpenRouter or OpenAI API key

## Setup

### 1. Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From scratch
2. Name: "Wingman", select your workspace
3. **OAuth & Permissions** - Add scopes: `app_mentions:read`, `channels:history`, `channels:read`, `chat:write`, `im:history`, `im:read`, `im:write`, `users:read`
4. Install to workspace, copy **Bot Token** (xoxb-*)
5. **Socket Mode** - Enable and generate **App Token** (xapp-*)
6. **Basic Information** - Copy **Signing Secret**
7. **Event Subscriptions** - Enable, subscribe to: `app_mention`, `message.im`

### 2. Configure

```bash
git clone https://github.com/echohello-dev/wingman.git
cd wingman
cp .env.example .env
# Edit .env with your tokens
```

### 3. Start

```bash
docker compose up -d
```

## Test

### In Slack

- **DM**: Send a message to @Wingman
- **Mention**: `@Wingman hello`
- **Command**: `/wingman hello`

You'll see **AI streaming** with thinking steps:
```
🧠 Processing your request...
  ✅ Analyzing question...
  🔍 Searching knowledge base...
  ✍️ Generating response...
  [Full answer]
```

## Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

## Common Commands

```bash
docker compose logs -f          # Watch logs
docker compose logs -f bot     # Bot logs specifically
docker compose ps               # Check status
docker compose restart bot      # Restart bot
docker compose down -v          # Clean stop
```

## Troubleshooting

**Bot not responding:**
```bash
docker compose logs -f bot
# Check SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET
```

**Database issues:**
```bash
docker compose down -v && docker compose up -d
```

## Next Steps

- [Local Development](docs/local-development.md) - Run bot locally with live streaming
- [Full Setup Docs](docs/setup.md) - Complete deployment guide
- [Slack Auth](docs/slack-auth.md) - Token reference

---

Happy chatting! 🛩
