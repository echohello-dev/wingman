# Setup Guide for Wingman

Complete setup guide for Wingman Slack support assistant with RAG.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- Git
- Slack workspace with admin access
- API key from [OpenRouter](https://openrouter.ai/) or [OpenAI](https://platform.openai.com/)

## Slack App Configuration

Wingman uses **Infrastructure as Code** to manage the Slack app via Terraform. This is the recommended approach.

### Option A: Automated Setup with Terraform (Recommended)

See [terraform.md](terraform.md) for complete setup instructions.

```bash
mise run tf-init    # Initialize Terraform
mise run tf-plan    # Review changes
mise run tf-apply   # Create Slack app
```

The app will be automatically created with all required scopes and configuration.

### Option B: Manual Setup

If you prefer to create the app manually:

1. Create app at [api.slack.com/apps](https://api.slack.com/apps) → From scratch
2. Name: "Wingman", select workspace
3. **OAuth & Permissions** - Add scopes:
   - `app_mentions:read`, `channels:history`, `channels:read`, `chat:write`
   - `im:history`, `im:read`, `im:write`, `users:read`
4. Install to workspace, copy **Bot User OAuth Token** (xoxb-*)
5. **Socket Mode** - Enable, generate **App-Level Token** (xapp-*)
6. **Event Subscriptions** - Subscribe to: `app_mention`, `message.im`
7. **Basic Information** - Copy **Signing Secret**

See [slack-auth.md](slack-auth.md) for token details.

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/echohello-dev/wingman.git
cd wingman
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Configure with Terraform (Recommended)

Follow [terraform.md](terraform.md) for complete setup:

```bash
# Initialize and create Slack app
mise run tf-init
mise run tf-plan
mise run tf-apply

# Install app to workspace (visit OAuth URL)
mise run tf-output | grep oauth_authorize_url

# Load credentials from Terraform
mise run tf-load-vars

# Manually add bot and app tokens after installing app to workspace
# Edit .env and add:
# SLACK_BOT_TOKEN=xoxb-...
# SLACK_APP_TOKEN=xapp-...
```

### 4. Configure Manually (Alternative)

If using manual setup, edit `.env` with your credentials:

```bash
# Required Slack Tokens (from manual app setup)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# Choose one: OpenRouter (recommended) or OpenAI
OPENROUTER_API_KEY=sk-or-your-openrouter-key-here
# OR
OPENAI_API_KEY=sk-your-openai-key-here

# Optional: Customize LLM model
LLM_MODEL=openai/gpt-4-turbo-preview
```

## Docker Deployment

### Start All Services

```bash
docker compose up -d
```

This starts:
- **Backend API** (port 8000)
- **Frontend Dashboard** (port 3000)
- **PostgreSQL** (port 5432)
- **ChromaDB** (port 8001)
- **Slack Bot** (Socket Mode)

### Verify Services

```bash
# Check service status
docker compose ps

# View logs
docker compose logs -f backend
docker compose logs -f bot
docker compose logs -f frontend

# Check backend health
curl http://localhost:8000/health
```

### Stop Services

```bash
docker compose down

# TConfiguration

```bash
git clone https://github.com/echohello-dev/wingman.git
cd wingman
cp .env.example .env
```

Edit `.env`:
```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...
OPENROUTER_API_KEY=sk-or-...  # or OPENAI_API_KEY=sk-...
```
# Install dependencies
npm install

# Start development server
npm run dev
```

Visit:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Testing the Bot

### In Slack

1. **Direct Message**: Send a DM to Wingman
   ```
   Hello, Wingman!
   ```

2. **Mention in Channel**: Invite bot to a channel and mention it
   ```
```bash
docker compose up -d
```

**Services:**
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: port 5432
- ChromaDB: port 8001


**Slack**: DM, mention (@Wingman), or /wingman command

**Dashboard**: http://localhost:3000

**API**:
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello!"}'

# See http://localhost:8000/docs for all endpoint

**Or use mise tasks:**
```bash
mise run dev-backend  # Terminal 1
mise run dev-frontend # Terminal 2
mise run dev-bot      # Terminal 3
```rts
services:
  backend:
    ports:
      - "8001:8000"  # Use 8001 instead of 8000
  frontend:
    ports:
      - "3001:3000"  # Use 3001 instead of 3000
```

### View Application Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f bot
docker compose logs -f frontend
docker compose logs -f postgres
docker compose logs -f chroma
```

## Next Steps

- **Index Documents**: Add documents to the knowledge base via API
- **Customize Prompts**: Edit `backend/app/rag.py` to customize the RAG prompt
- **Add Reactions**: Implement feedback collection via Slack reactions
- **Deploy to Production**: Use a proper web server and HTTPS for production
- **Monitor Usage**: Track LLM API costs and usage

| Issue | Solution |
|-------|----------|
| Bot not responding | Check `docker compose logs bot`, verify Socket Mode enabled, check tokens with xoxb-/xapp- prefixes |
| Database errors | `docker compose logs postgres`, verify DATABASE_URL in .env |
| Can't access services | Run `docker compose ps`, verify ports aren't in use |
| Port conflicts | Edit docker-compose.yaml to use different ports (e.g., 8001 instead of 8000) |
| Invalid API key | Verify key format and credits in OpenRouter/OpenAI account |

**Reset everything**: `docker compose down -v && docker compose up -d`

**View logs**: `docker compose logs -f <service>` (backend, bot, frontend, postgres, chroma)

## Production Deployment

- Use managed PostgreSQL (AWS RDS, etc.)
- Deploy Chroma in production mode
- Use secret management (AWS Secrets Manager, Vault, etc.)
- Enable HTTPS for HTTP mode
- Set up monitoring and alerts
- Regular backups for database and vector store
- Rotate tokens periodically

See [slack-auth.md](slack-auth.md) for authentication details.