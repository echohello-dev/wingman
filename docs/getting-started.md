# Quick Start Guide

Get Wingman up and running in minutes!

## Prerequisites

- Docker and Docker Compose
- Slack workspace admin access
- OpenRouter or OpenAI API key

## Setup Steps

### 1. Slack Configuration

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From scratch
2. Name: "Wingman", select your workspace
3. **OAuth & Permissions** - Add scopes: `app_mentions:read`, `channels:history`, `channels:read`, `chat:write`, `im:history`, `im:read`, `im:write`, `users:read`
4. Install to workspace, copy **Bot Token** (xoxb-*)
5. **Socket Mode** - Enable and generate **App Token** (xapp-*)
6. **Basic Information** - Copy **Signing Secret**

### 2. Get API Key

- **OpenRouter** (recommended): [openrouter.ai](https://openrouter.ai/)
- **OpenAI**: [platform.openai.com](https://platform.openai.com/)

### 3. Configure & Start

```bash
git clone https://github.com/echohello-dev/wingman.git
cd wingman
cp .env.example .env
# Edit .env with your tokens
docker compose up -d
```

**Access:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Testing

**Slack**: DM, mention (@Wingman), or slash command (/wingman)

**API**:
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello!"}'
```

## Common Commands

```bash
docker compose logs -f          # View logs
docker compose ps               # Check services
docker compose restart backend  # Restart service
docker compose down -v          # Stop and clean
```

## Troubleshooting

**Bot not responding**: Check `docker compose logs -f bot` and verify environment variables

**Can't access dashboard**: Run `docker compose ps` to verify services are running

**Database issues**: Run `docker compose down -v && docker compose up -d`

## Next Steps

- Index documents: See API docs at http://localhost:8000/docs
- Customize prompts: Edit `backend/app/rag.py`
- [Full docs](../setup.md) and [Slack auth details](slack-auth.md)

---

Happy chatting! 🛩️
