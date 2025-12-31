---
date: 2024-12-31
status: Accepted
---

# 0001: Technology Stack and RAG Architecture

## Context

Wingman was created as an open-source Slack support assistant that can provide intelligent, context-aware responses based on Slack conversations and documentation. The project needed to:

1. Integrate deeply with Slack for mentions, DMs, and slash commands
2. Provide AI-powered responses using retrieval-augmented generation (RAG)
3. Support a modern web dashboard for management
4. Be easy to deploy and run locally for evaluation
5. Support multiple LLM providers (OpenAI, OpenRouter)

The original request (from PR #1) was:

> "Create an OSS monorepo for a Slack support assistant: Python FastAPI + Slack Bolt backend (RAG over Slack threads/docs via LangChain + OpenRouter) and Next.js/TS dashboard. Include Postgres + Chroma, Dockerfiles and docker-compose for local eval, .env examples, and docs."

## Decision

We chose the following technology stack:

### Backend: Python + FastAPI + Slack Bolt

- **FastAPI** as the REST API framework for the backend service
- **Slack Bolt** for Python as the Slack integration SDK
- **uv** as the Python package manager for fast, reliable dependency installation
- **Python 3.14** as the runtime version

### RAG Pipeline: LangChain + ChromaDB

- **LangChain** as the orchestration framework for the RAG pipeline
- **LangChain-OpenAI** for LLM integration with OpenAI-compatible APIs
- **ChromaDB** as the vector database for semantic search and embeddings
- **OpenAI Embeddings** (`text-embedding-ada-002`) for document vectorization

### LLM Provider: OpenRouter (Primary) / OpenAI (Fallback)

- **OpenRouter** as the recommended LLM provider for access to multiple models
- **OpenAI** as an alternative direct provider
- Configurable model selection via `LLM_MODEL` environment variable

### Database: PostgreSQL

- **PostgreSQL 16** for persistent storage of messages and documents
- **SQLAlchemy** as the ORM layer

### Frontend: Next.js + TypeScript

- **Next.js 16** (App Router) for the management dashboard
- **TypeScript** with ES2022 target
- **Tailwind CSS v4.1** with CSS-based theme configuration
- **Bun** as the package manager and runtime

### Infrastructure: Docker Compose

- Multi-service orchestration with `compose.yaml`
- Service-specific environment files (`.env.postgres`, `.env.chroma`, `.env.backend`, `.env.frontend`)
- Socket Mode support for local development (no public URL required)

### Tooling: mise

- **mise.toml** for unified task runner and tool version management
- Tasks for common operations: `mise run up`, `mise run dev-backend`, `mise run test-backend`

## Alternatives Considered

### Alternative 1: LlamaIndex instead of LangChain

LlamaIndex is another popular framework for building RAG applications with strong indexing capabilities.

**Why not chosen:**
- LangChain has broader ecosystem support and more examples
- LangChain's modular design allows easier swapping of components (LLMs, vector stores)
- Better OpenRouter integration out of the box
- More familiar to the Python AI/ML community

### Alternative 2: Pinecone instead of ChromaDB

Pinecone is a managed vector database service with strong performance characteristics.

**Why not chosen:**
- ChromaDB is open-source and can run locally without external dependencies
- No account or API key required for local development
- Easier to include in Docker Compose for self-contained deployments
- Sufficient for the expected scale of Slack workspace data
- Lower barrier to entry for OSS contributors

### Alternative 3: Direct OpenAI SDK instead of LangChain

Using the OpenAI SDK directly would reduce dependencies and complexity.

**Why not chosen:**
- LangChain provides RAG-specific abstractions (chains, retrievers, prompts)
- Easier to add features like conversation memory, agents, or tool use
- Built-in integration with ChromaDB and other vector stores
- Prompt templating and management out of the box
- Supports multiple LLM providers through a unified interface

### Alternative 4: Flask instead of FastAPI

Flask is a mature, widely-used Python web framework.

**Why not chosen:**
- FastAPI provides automatic OpenAPI documentation
- Built-in async support for better performance
- Native Pydantic integration for request/response validation
- Modern Python type hints throughout
- Better suited for API-first applications

### Alternative 5: npm/pnpm instead of Bun

Traditional Node.js package managers are more widely adopted.

**Why not chosen:**
- Bun provides significantly faster installation and build times
- Built-in TypeScript support
- Simpler toolchain (single binary)
- Actively developed with growing ecosystem support

## Consequences

### Positive

- **Unified RAG pipeline**: LangChain provides a cohesive framework for retrieval, prompting, and generation
- **Local-first development**: ChromaDB + Docker Compose enables fully local evaluation without external services
- **LLM flexibility**: OpenRouter support allows access to multiple model providers (OpenAI, Anthropic, etc.) through a single API
- **Type safety**: FastAPI + Pydantic on backend, TypeScript on frontend ensure strong typing throughout
- **Developer experience**: mise tasks, hot reload, and comprehensive documentation lower the barrier to contribution
- **Slack-native**: Slack Bolt provides production-ready event handling, Socket Mode for development, and proper request verification

### Negative

- **LangChain overhead**: LangChain adds abstraction layers that may complicate debugging in some cases
- **ChromaDB scaling limits**: For very large knowledge bases, a managed vector database might be more appropriate
- **Python 3.14 requirement**: Cutting-edge Python version may require extra setup on some systems
- **Multiple moving parts**: Five Docker services (backend, bot, frontend, postgres, chroma) increase operational complexity
- **OpenAI dependency for embeddings**: Even when using OpenRouter for LLM, embeddings still require OpenAI API access

## References

- [PR #1: Implement OSS monorepo for Slack support assistant](https://github.com/echohello-dev/wingman/pull/1)
- [Commit fae8448: Add complete OSS monorepo structure](https://github.com/echohello-dev/wingman/commit/fae8448)
- [Commit 4dc951d: Modernize project with mise.toml, compose.yaml, Python 3.14](https://github.com/echohello-dev/wingman/commit/4dc951d)
- [LangChain Documentation](https://python.langchain.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Slack Bolt for Python](https://slack.dev/bolt-python/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
