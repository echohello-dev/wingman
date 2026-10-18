# Pi Durable runtime

Wingman uses Pi Durable for model turns and agent conversation memory. Python
retrieves context from Chroma and submits it to the runtime. Slack inputs are
acknowledged after admission to a persistent outbox; the runtime generates and
posts the final answer, including after a restart.

## Run with Docker

Set `PI_RUNTIME_TOKEN` in the root `.env` to a random secret (for example, generate
one with `openssl rand -hex 32`). Both Python services and the runtime read it.
Set `OPENROUTER_API_KEY` and an OpenRouter `LLM_MODEL`, or `OPENAI_API_KEY` and an
OpenAI model ID. The runtime checks the model against Pi's bundled catalog at
startup. Use `openai/gpt-4.1` for OpenRouter or `gpt-4.1` for OpenAI.
For a direct MiMo Singapore token plan, set `PI_PROVIDER=mimo`,
`LLM_MODEL=mimo-v2.6-flash` (or `mimo-v2.6-pro`), and
`XIAOMI_TOKEN_PLAN_SGP_API_KEY`. Explicit provider selection takes precedence over
OpenRouter auto-detection. The API key can be supplied to the runtime process
environment without copying Pi's credential store into the project.
`LLM_TEMPERATURE` and `LLM_MAX_TOKENS` still configure model calls.

```sh
mise run up
```

Compose builds the runtime and mounts `pi_data` at `/data`. Keep this volume across
restarts. `mise run clean` deletes it along with the other database volumes.
Do not run multiple runtime processes against the same data directory.

## Local development

Use Node 24 or newer. Install and start the runtime alongside the Python services:

```sh
mise run install-runtime
mise run dev-runtime
```

The task loads the root `.env`; set `PI_RUNTIME_URL=http://localhost:8002` for
Python and `PI_DATA_DIR` if you want a location other than `runtime/data`.
Local data files contain conversation content and must be treated as private.

```sh
mise run test-runtime
mise run test-backend
```

The runtime tests use Pi's faux model provider with real SQLite storage. They
exercise persisted answers, conversation memory, duplicate submission, abrupt
process death during generation, and outbox restart after a delivery failure.

## API requests and retries

`POST /api/ask` retains its answer/sources/confidence response. It accepts optional
`conversation_id` and `request_id` fields. Reuse the same request ID to recover a
response after a timeout; use a new request ID for a new question. Omitting the
conversation ID isolates the request. Supplying the same ID continues Pi history.

The internal runtime exposes authenticated `POST /jobs` and `GET /jobs/{id}`.
The submitted job ID is the SHA-256 hash of the request ID. Its states are
`pending`, `delivering`, `done`, `failed`, or `delivery_failed`. It is not published
to the host in Compose. For inspection, access it from the Compose network with
`Authorization: Bearer <PI_RUNTIME_TOKEN>`. Failed jobs remain available for
inspection; after fixing the cause, submit a new request ID to run the question
again. Do not automatically replay a delivery failure without checking Slack,
since a lost acknowledgement may mean the original message was already posted.

Pi history replaces the old conversation timeout/window behaviour for new turns.
Old PostgreSQL history remains readable but is not imported automatically. Slack
uses final messages; the earlier temporary progress streams are no longer used.

## Live MiMo smoke test with Pi's credential

After `mise run install-backend`, if Pi stores a `mimo` API-key credential in
`~/.pi/agent/auth.json`, run:

```sh
mise run test-runtime-live
```

This opt-in test makes three small MiMo Flash requests against the Singapore token
plan endpoint. It passes the key only to the child runtime environment, uses a
temporary data directory, kills/restarts the runtime after admitting a request,
then checks the grounded answer, idempotent replay, the Python backend client,
follow-up memory, and conversation isolation. It does not post to Slack or change Pi's credential files.
