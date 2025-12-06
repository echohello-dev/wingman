# 🛩️ Wingman - Slack Support Assistant

An AI-powered Slack support assistant with RAG (Retrieval Augmented Generation) capabilities. Wingman uses LangChain and OpenRouter to provide intelligent responses based on your Slack threads, conversations, and documentation.

## 🌟 Features

- **🤖 Slack Integration**: Full Slack Bolt SDK integration with support for mentions, DMs, and slash commands
- **🧠 RAG-Powered Responses**: Uses LangChain + OpenRouter/OpenAI for context-aware answers
- **📚 Knowledge Base**: Index Slack threads and documents for intelligent retrieval
- **💾 Vector Storage**: ChromaDB for efficient semantic search
- **🗄️ PostgreSQL Database**: Persistent storage for messages and documents
- **📊 Next.js Dashboard**: Modern TypeScript dashboard for managing the assistant
- **🐳 Docker Ready**: Complete docker-compose setup for local development

## 🏗️ Architecture

```
wingman/
├── backend/           # Python FastAPI + Slack Bolt backend
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── slack_bot.py      # Slack Bolt bot
│   │   ├── rag.py            # RAG engine
│   │   ├── vector_store.py   # Chroma integration
│   │   ├── database.py       # PostgreSQL models
│   │   └── config.py         # Configuration
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/          # Next.js/TypeScript dashboard
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── Dockerfile
├── docs/              # Documentation
│   ├── SETUP.md
│   └── SLACK_AUTH.md
├── docker-compose.yml
└── .env.example
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Slack workspace with admin access
- OpenRouter or OpenAI API key

### 1. Clone the Repository

```bash
git clone https://github.com/echohello-dev/wingman.git
cd wingman
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
- `SLACK_BOT_TOKEN`: Bot User OAuth Token (xoxb-*)
- `SLACK_APP_TOKEN`: App-Level Token (xapp-*) for Socket Mode
- `SLACK_SIGNING_SECRET`: Signing secret from Slack app settings
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY`: API key for LLM

See [SLACK_AUTH.md](docs/SLACK_AUTH.md) for detailed Slack setup instructions.

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- **Backend API** on http://localhost:8000
- **Frontend Dashboard** on http://localhost:3000
- **PostgreSQL** on port 5432
- **ChromaDB** on port 8001
- **Slack Bot** in Socket Mode

### 4. Verify Installation

```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f bot
```

Visit http://localhost:3000 to access the dashboard.

## 📖 Documentation

- **[SETUP.md](docs/SETUP.md)**: Detailed setup and configuration guide
- **[SLACK_AUTH.md](docs/SLACK_AUTH.md)**: Slack authentication and token types

## 🔧 Usage

### In Slack

1. **Mention the bot**: `@Wingman How do I reset my password?`
2. **Use slash command**: `/wingman What are the API rate limits?`
3. **Direct message**: Send a DM to Wingman for private assistance

### Via Dashboard

1. Navigate to http://localhost:3000
2. Ask questions in the "Ask Question" tab
3. View indexed documents and messages

### Via API

```bash
# Ask a question
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I authenticate?"}'

# Add a document
curl -X POST http://localhost:8000/api/documents \
  -H "Content-Type: application/json" \
  -d '{"title": "API Docs", "content": "...", "source": "docs"}'
```

## 🛠️ Development

### Local Development (without Docker)

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL and Chroma separately or use Docker for them
docker-compose up -d postgres chroma

# Run backend
python -m uvicorn app.main:app --reload

# Run bot separately
python run_bot.py
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 🔐 Security Notes

- Never commit `.env` files or secrets
- Use environment-specific tokens for development/production
- Rotate tokens regularly
- Follow the principle of least privilege for Slack scopes
- Review [SLACK_AUTH.md](docs/SLACK_AUTH.md) for security best practices

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- [Slack Bolt](https://slack.dev/bolt-python/tutorial/getting-started) for Python
- [LangChain](https://www.langchain.com/) for RAG capabilities
- [OpenRouter](https://openrouter.ai/) for LLM access
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [Next.js](https://nextjs.org/) for the dashboard

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check the [documentation](docs/)
- Review Slack API docs at https://api.slack.com/

---

Made with ❤️ for better Slack support
