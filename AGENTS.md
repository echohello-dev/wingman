# AI Agent Instructions for Wingman

## Architecture Overview

Wingman is a Slack support assistant with RAG (Retrieval Augmented Generation) capabilities. The system has **four main services**:

| Service | Technology | Purpose |
|---------|------------|---------|
| `backend` | FastAPI (Python 3.14) | REST API for questions, documents, messages |
| `bot` | Slack Bolt (Python) | Socket Mode Slack bot handling mentions/DMs |
| `frontend` | Next.js 16 + React 19 | Dashboard UI at port 3000 |
| `postgres` | PostgreSQL 16 | Stores messages and documents |
| `chroma` | ChromaDB | Vector store for embeddings |

**Key insight**: The `backend` and `bot` services share the same codebase (`/backend`) but run different entrypoints (`uvicorn` vs `python run_bot.py`).

## Developer Workflow Commands

**Use `mise run` for all tasks** (not `make` - the Makefile exists but mise.toml is authoritative):

```bash
mise run install          # Install all deps (uv for backend, bun for frontend)
mise run up               # Start all services via docker compose
mise run down             # Stop services
mise run logs-backend     # Tail backend logs
mise run test-backend     # Run pytest via uv
mise run dev-backend      # Run backend locally with hot reload
mise run dev-bot          # Run Slack bot locally
mise run shell-db         # psql into PostgreSQL
```

## Backend Patterns

### Configuration (`backend/app/config.py`)
- Uses `pydantic-settings` for env validation
- All config via `Settings` class, accessed as `from app.config import settings`
- Supports both OpenRouter (`OPENROUTER_API_KEY`) and OpenAI (`OPENAI_API_KEY`)

### Global Singletons
These are instantiated at module import time—do not recreate:
- `rag_engine` from `app.rag` — handles LLM + retrieval
- `vector_store` from `app.vector_store` — ChromaDB wrapper
- `slack_bot` from `app.slack_bot` — Slack Bolt app

### RAG Flow (`backend/app/rag.py`)
1. `rag_engine.generate_response(question, channel_id)` → searches Chroma → prompts LLM
2. `rag_engine.index_slack_thread(messages, channel_id)` → indexes thread messages
3. Uses LangChain's `ChatOpenAI` with custom prompt template

### Database Models (`backend/app/database.py`)
- `SlackMessage`: stores Slack events with `message_ts` as unique key
- `Document`: knowledge base entries indexed in Chroma
- Use `get_db()` as FastAPI dependency for sessions

### API Endpoints (`backend/app/main.py`)
| Endpoint | Purpose |
|----------|---------|
| `POST /api/ask` | Query the RAG system |
| `POST /api/documents` | Add document to knowledge base |
| `GET /api/documents` | List documents |
| `GET /api/messages` | List stored Slack messages |
| `POST /api/index/thread` | Index a specific thread |

## Frontend Patterns

- **Package manager**: Bun (not npm)
- Uses Next.js App Router (`frontend/app/`)
- API client expected at `@/lib/api` (needs implementation if missing)
- Tailwind CSS v4 for styling

## Environment Configuration

Copy `.env.example` to `.env`. Key variables:
- `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET` — Slack credentials
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` — LLM provider
- Docker services use hostnames `postgres`, `chroma`; local dev uses `localhost`

## Testing

```bash
cd backend && uv test      # Backend tests (pytest-asyncio)
cd frontend && bun test    # Frontend tests
```

Backend tests use `TestClient` from FastAPI—see `backend/tests/test_api.py` for patterns.

## Common Pitfalls

1. **Chroma port mapping**: Container exposes 8000, but host maps to 8001 (`localhost:8001`)
2. **Missing lib/api**: Frontend imports from `@/lib/api` which may need creation
3. **Socket Mode**: Bot requires `SLACK_APP_TOKEN` for local dev; production uses Events API
4. **Embeddings**: Both Chroma indexing and RAG require OpenAI API key for `text-embedding-ada-002`
