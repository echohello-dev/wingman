# Wingman

AI-powered Slack support assistant with RAG capabilities. Answers questions using your indexed documents via LangChain and OpenRouter/OpenAI.

## Quick Start

```bash
git clone https://github.com/echohello-dev/wingman.git
cd wingman
cp .env.example .env
# Edit .env with your Slack tokens and API keys
docker compose up -d
```

Access: [Backend](http://localhost:8000) • [Dashboard](http://localhost:3000) • [API Docs](http://localhost:8000/docs)

See [docs/setup.md](docs/setup.md) and [docs/getting-started.md](docs/getting-started.md) for detailed setup.

## Architecture

FastAPI backend with Slack bot, RAG engine (LangChain + ChromaDB), PostgreSQL storage, and Next.js dashboard. See [ADR-0001](docs/adrs/0001-technology-stack-and-rag-architecture.md) for architecture decisions.

## Development

See [contributing.md](contributing.md) for development workflow, commands, and guidelines.

**For AI coding agents:** [AGENTS.md](AGENTS.md) contains architecture and command reference for automated development.

## Documentation

**Setup & Usage:**
- [docs/setup.md](docs/setup.md) - Installation & configuration
- [docs/getting-started.md](docs/getting-started.md) - Quick reference
- [docs/slack-auth.md](docs/slack-auth.md) - Slack authentication
- [docs/terraform.md](docs/terraform.md) - Infrastructure as code

**Architecture Decisions:**
- [docs/adrs/](docs/adrs/) - All ADRs
- [ADR-0001](docs/adrs/0001-technology-stack-and-rag-architecture.md) - Tech stack & RAG
- [ADR-0002](docs/adrs/0002-release-please-for-monorepo-versioning.md) - Versioning
- [ADR-0003](docs/adrs/0003-terraform-slack-app-iac.md) - Terraform

## Contributing

Contributions welcome! See [contributing.md](contributing.md) for guidelines.

## License

MIT License

## Built With

[FastAPI](https://fastapi.tiangolo.com/) • [Slack Bolt](https://slack.dev/bolt-python/) • [LangChain](https://www.langchain.com/) • [OpenRouter](https://openrouter.ai/) • [ChromaDB](https://www.trychroma.com/) • [Next.js](https://nextjs.org/)

---

Made with care for better Slack support
