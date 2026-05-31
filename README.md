# Wingman

AI-powered Slack support assistant with RAG capabilities and **AI streaming with thinking steps**. Watch the bot's reasoning process in real-time as it searches knowledge bases and generates responses.

## Features

- **AI Streaming**: See the bot think in real-time with Thinking Steps
- **RAG-powered Answers**: Uses indexed documents via LangChain + ChromaDB
- **Multi-channel Support**: DMs, mentions, slash commands
- **Document Indexing**: Auto-index files shared in Slack

## Quick Start

```bash
git clone https://github.com/echohello-dev/wingman.git
cd wingman
cp .env.example .env
# Edit .env with your Slack tokens and API keys
docker compose up -d
```

Access: [Backend](http://localhost:8000) • [Dashboard](http://localhost:3000) • [API Docs](http://localhost:8000/docs)

## Test It

In Slack:
- **DM**: Send a message to @Wingman
- **Mention**: `@Wingman what's up?`
- **Command**: `/wingman hello`

You'll see streaming thinking steps as the bot processes your request.

## Documentation

| Guide | Purpose |
|-------|---------|
| [Getting Started](docs/getting-started.md) | Quick start |
| [Local Development](docs/local-development.md) | Run locally with streaming |
| [Setup Guide](docs/setup.md) | Full deployment |
| [Slack Auth](docs/slack-auth.md) | Token reference |

## Architecture

FastAPI backend with Slack bot, RAG engine (LangChain + ChromaDB), PostgreSQL storage, and Next.js dashboard. See [ADR-0001](docs/adrs/0001-technology-stack-and-rag-architecture.md) for architecture decisions.

## Development

See [contributing.md](contributing.md) for development workflow, commands, and guidelines.

**For AI coding agents:** [AGENTS.md](AGENTS.md) contains architecture and command reference for automated development.

## Documentation

See [./docs](docs/) for setup guides and [./docs/adrs](docs/adrs/) for architecture decisions.

## Contributing

Contributions welcome! See [contributing.md](contributing.md) for guidelines.

## License

See [LICENSE](LICENSE) for details.

## Built With

[FastAPI](https://fastapi.tiangolo.com/) • [Slack Bolt](https://slack.dev/bolt-python/) • [LangChain](https://www.langchain.com/) • [OpenRouter](https://openrouter.ai/) • [ChromaDB](https://www.trychroma.com/) • [Next.js](https://nextjs.org/)

---

Made with care for better Slack support
