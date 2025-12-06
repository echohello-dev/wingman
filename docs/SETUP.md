# Setup Guide for Wingman

This guide will walk you through setting up Wingman, a Slack support assistant with RAG capabilities.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Slack App Configuration](#slack-app-configuration)
3. [Environment Setup](#environment-setup)
4. [Docker Deployment](#docker-deployment)
5. [Local Development](#local-development)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Git** for cloning the repository
- **Slack workspace** with admin permissions
- **API Key** from OpenRouter or OpenAI

### Getting API Keys

#### OpenRouter (Recommended)

1. Visit [OpenRouter](https://openrouter.ai/)
2. Sign up or log in
3. Navigate to [Keys](https://openrouter.ai/keys)
4. Create a new API key
5. Copy the key (starts with `sk-or-`)

#### OpenAI (Alternative)

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to [API Keys](https://platform.openai.com/api-keys)
4. Create a new API key
5. Copy the key (starts with `sk-`)

## Slack App Configuration

### 1. Create a Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Select **"From scratch"**
4. Enter app name: `Wingman`
5. Select your workspace
6. Click **"Create App"**

### 2. Configure Bot Token Scopes

Navigate to **OAuth & Permissions** and add these Bot Token Scopes:

**Required Scopes:**
- `app_mentions:read` - View messages that directly mention @yourbot
- `channels:history` - View messages in public channels
- `channels:read` - View basic information about public channels
- `chat:write` - Post messages in channels
- `im:history` - View messages in direct messages
- `im:read` - View basic information about direct messages
- `im:write` - Start direct messages with people
- `users:read` - View people in the workspace
- `reactions:read` - View emoji reactions (optional)

**Optional Scopes (for advanced features):**
- `channels:join` - Join public channels
- `groups:history` - View messages in private channels
- `groups:read` - View basic information about private channels

### 3. Install App to Workspace

1. In **OAuth & Permissions**, click **"Install to Workspace"**
2. Review permissions and click **"Allow"**
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
4. Save this token for your `.env` file

### 4. Enable Socket Mode (for development)

Socket Mode allows your bot to receive events without exposing a public URL.

1. Navigate to **Socket Mode** in the sidebar
2. Toggle **"Enable Socket Mode"** to ON
3. Give the token a name (e.g., "Wingman App Token")
4. Click **"Generate"**
5. Copy the **App-Level Token** (starts with `xapp-`)
6. Save this token for your `.env` file

### 5. Subscribe to Events

1. Navigate to **Event Subscriptions**
2. For Socket Mode: It should be automatically enabled
3. For HTTP Mode (production): Enter your Request URL (e.g., `https://yourdomain.com/slack/events`)

**Subscribe to Bot Events:**
- `app_mention` - When the bot is mentioned
- `message.im` - Messages in direct messages
- `reaction_added` - When reactions are added (optional)

### 6. Configure Interactivity

1. Navigate to **Interactivity & Shortcuts**
2. Toggle **"Interactivity"** to ON
3. For Socket Mode: Leave URL empty
4. For HTTP Mode: Enter your Request URL

### 7. Add Slash Command (Optional)

1. Navigate to **Slash Commands**
2. Click **"Create New Command"**
3. Configure:
   - Command: `/wingman`
   - Request URL: Leave empty for Socket Mode
   - Short Description: "Ask Wingman for help"
   - Usage Hint: "your question here"
4. Click **"Save"**

### 8. Get Signing Secret

1. Navigate to **Basic Information**
2. Under **App Credentials**, find **Signing Secret**
3. Click **"Show"** and copy the secret
4. Save this for your `.env` file

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

### 3. Configure Environment Variables

Edit `.env` with your credentials:

```bash
# Required Slack Tokens
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

See [SLACK_AUTH.md](SLACK_AUTH.md) for more details on token types.

## Docker Deployment

### Start All Services

```bash
docker-compose up -d
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
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f bot
docker-compose logs -f frontend

# Check backend health
curl http://localhost:8000/health
```

### Stop Services

```bash
docker-compose down

# To also remove volumes (data)
docker-compose down -v
```

## Local Development

For development without Docker:

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start dependencies (or use local Postgres/Chroma)
docker-compose up -d postgres chroma

# Run backend API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In a separate terminal, run the bot
python run_bot.py
```

### Frontend Setup

```bash
cd frontend

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
   @Wingman How do I reset my password?
   ```

3. **Slash Command**: Use the slash command
   ```
   /wingman What are the API rate limits?
   ```

### Via Dashboard

1. Open http://localhost:3000
2. Navigate to "Ask Question" tab
3. Enter a question and click "Ask Wingman"

### Via API

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I authenticate?"}'

# Add a document
curl -X POST http://localhost:8000/api/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Authentication Guide",
    "content": "To authenticate, use your API key...",
    "source": "docs"
  }'

# List messages
curl http://localhost:8000/api/messages
```

## Troubleshooting

### Bot Not Responding in Slack

**Check:**
1. Bot is running: `docker-compose logs bot`
2. Socket Mode is enabled in Slack app settings
3. `SLACK_APP_TOKEN` is set correctly (starts with `xapp-`)
4. Bot is invited to the channel (for mentions)
5. Bot has required permissions

**Common Issues:**
- "Invalid token": Check `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`
- "Not in channel": Invite bot with `/invite @Wingman`
- "Permission denied": Review OAuth scopes

### Database Connection Issues

```bash
# Check PostgreSQL
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U wingman -d wingman

# Verify connection string in .env
DATABASE_URL=postgresql://wingman:wingman@postgres:5432/wingman
```

### Vector Store Issues

```bash
# Check Chroma
docker-compose logs chroma

# Verify Chroma is running
curl http://localhost:8001/api/v1/heartbeat

# Reset Chroma data
docker-compose down -v
docker-compose up -d chroma
```

### LLM/API Issues

**OpenRouter:**
- Verify API key is valid
- Check account credits at https://openrouter.ai/account
- Review model name format: `openai/gpt-4-turbo-preview`

**OpenAI:**
- Verify API key is valid
- Check account credits at https://platform.openai.com/usage
- Review model name format: `gpt-4-turbo-preview`

### Port Conflicts

If ports are already in use:

```bash
# Edit docker-compose.yml to change ports
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
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f bot
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f chroma
```

## Next Steps

- **Index Documents**: Add documents to the knowledge base via API
- **Customize Prompts**: Edit `backend/app/rag.py` to customize the RAG prompt
- **Add Reactions**: Implement feedback collection via Slack reactions
- **Deploy to Production**: Use a proper web server and HTTPS for production
- **Monitor Usage**: Track LLM API costs and usage

## Production Considerations

1. **Security**:
   - Use environment-specific tokens
   - Enable HTTPS for webhook endpoints
   - Rotate tokens regularly
   - Restrict database access

2. **Scalability**:
   - Use managed PostgreSQL (AWS RDS, etc.)
   - Deploy Chroma in production mode
   - Use proper secret management (AWS Secrets Manager, etc.)
   - Add rate limiting

3. **Monitoring**:
   - Add application logging
   - Monitor LLM costs
   - Track bot performance
   - Set up alerts

4. **Backup**:
   - Regular database backups
   - Vector store backups
   - Configuration backups

For more details, see [SLACK_AUTH.md](SLACK_AUTH.md) for authentication options.
