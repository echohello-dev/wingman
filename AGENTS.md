# AI Agent Instructions for Wingman

## Architecture

Slack support assistant with RAG capabilities. Four services in `compose.yaml`:

- **backend** (FastAPI) — REST API at port 8000
- **bot** (Slack Bolt) — Socket Mode bot for mentions/DMs
- **frontend** (Next.js) — Dashboard at port 3000
- **postgres** + **chroma** — Data storage and vector embeddings

**Key**: `backend` and `bot` share `/backend` codebase with different entrypoints.

## Commands

Use `mise run` (not `make`):

```bash
mise run install        # uv for backend, bun for frontend
mise run up / down      # Docker services
mise run dev-backend    # Local backend with reload
mise run dev-bot        # Local Slack bot
mise run test-backend   # pytest via uv
mise run shell-db       # psql into postgres
```

## Backend (`/backend`)

**Config**: `app/config.py` — access via `from app.config import settings`

**Singletons** (module-level, don't recreate):
- `rag_engine` from `app.rag`
- `vector_store` from `app.vector_store`
- `slack_bot` from `app.slack_bot`

**Database**: `app/database.py` — use `get_db()` as FastAPI dependency

**API routes** in `app/main.py`: `/api/ask`, `/api/documents`, `/api/messages`

## Frontend (`/frontend`)

- Package manager: **Bun**
- App Router in `frontend/app/`
- API client at `@/lib/api`

## Environment

Copy `.env.example` to `.env`. Docker uses hostnames (`postgres`, `chroma`); local dev uses `localhost`.

**Chroma port**: Container 8000 → host 8001
