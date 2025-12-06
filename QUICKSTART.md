# Quick Start Guide

Get Wingman up and running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Slack workspace admin access
- OpenRouter or OpenAI API key

## Step 1: Get Your Slack Tokens

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Name it "Wingman" and select your workspace
4. In **OAuth & Permissions**, add these scopes:
   - `app_mentions:read`
   - `channels:history`
   - `channels:read`
   - `chat:write`
   - `im:history`
   - `im:read`
   - `im:write`
   - `users:read`
5. Click **"Install to Workspace"** and copy the **Bot Token** (xoxb-*)
6. In **Socket Mode**, enable it and generate an **App Token** (xapp-*)
7. In **Basic Information**, copy the **Signing Secret**

## Step 2: Get Your AI API Key

**Option A: OpenRouter (Recommended)**
- Visit [openrouter.ai](https://openrouter.ai/)
- Sign up and get your API key

**Option B: OpenAI**
- Visit [platform.openai.com](https://platform.openai.com/)
- Sign up and get your API key

## Step 3: Configure Wingman

```bash
# Clone the repo
git clone https://github.com/echohello-dev/wingman.git
cd wingman

# Copy the environment template
cp .env.example .env

# Edit .env with your tokens
# Required:
# - SLACK_BOT_TOKEN=xoxb-...
# - SLACK_APP_TOKEN=xapp-...
# - SLACK_SIGNING_SECRET=...
# - OPENROUTER_API_KEY=... (or OPENAI_API_KEY)
```

## Step 4: Start Wingman

```bash
docker-compose up -d
```

This starts:
- Backend API: http://localhost:8000
- Frontend Dashboard: http://localhost:3000
- PostgreSQL database
- ChromaDB vector store
- Slack bot

## Step 5: Test It!

### In Slack:
1. Send a DM to Wingman: `Hello!`
2. Or mention in a channel: `@Wingman How can you help me?`
3. Or use slash command: `/wingman What are you?`

### In Dashboard:
1. Open http://localhost:3000
2. Type a question in the "Ask Question" tab
3. Click "Ask Wingman"

### Via API:
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello, who are you?"}'
```

## Troubleshooting

### Bot not responding?
```bash
# Check logs
docker-compose logs -f bot

# Verify environment
docker-compose exec bot env | grep SLACK
```

### Can't access dashboard?
```bash
# Check if services are running
docker-compose ps

# Check frontend logs
docker-compose logs -f frontend
```

### Database issues?
```bash
# Restart all services
docker-compose restart

# Or recreate everything
docker-compose down -v
docker-compose up -d
```

## What's Next?

1. **Add Documents**: Index your documentation for better answers
   ```bash
   curl -X POST http://localhost:8000/api/documents \
     -H "Content-Type: application/json" \
     -d '{
       "title": "My Guide",
       "content": "Content here...",
       "source": "docs"
     }'
   ```

2. **Customize Prompts**: Edit `backend/app/rag.py` to customize responses

3. **Monitor Usage**: Check API docs at http://localhost:8000/docs

4. **Read Full Docs**:
   - [SETUP.md](docs/SETUP.md) - Detailed setup guide
   - [SLACK_AUTH.md](docs/SLACK_AUTH.md) - Authentication details
   - [README.md](README.md) - Full documentation

## Common Commands

```bash
# View all logs
docker-compose logs -f

# Stop everything
docker-compose down

# Restart a service
docker-compose restart backend

# Access database
docker-compose exec postgres psql -U wingman -d wingman

# Run backend tests
cd backend && pytest

# Update dependencies
docker-compose build
```

## Getting Help

- 📖 Read the [full documentation](README.md)
- 🐛 [Open an issue](https://github.com/echohello-dev/wingman/issues)
- 💬 Check [Slack API docs](https://api.slack.com/)

---

Happy chatting! 🛩️
