# Structured logging baseline (Wingman #7)

## Schema

The `backend` (FastAPI) and `bot` (Slack Bolt) services share the `/backend`
codebase and emit one JSON object per line to **stdout** by default.
`backend/app/logging.py` provides settings-based `configure_logging()` and
re-exports `JsonFormatter`; both use the implementation in
`backend/app/logging_config.py`, including its redaction and request correlation.

Tracked in [echohello-dev/wingman#7](https://github.com/echohello-dev/wingman/issues/7).

| Field | Notes |
|---|---|
| `timestamp`, `level`, `logger`, `message` | ISO-8601 UTC, stdlib level, module name |
| `service_name`, `service_version`, `environment` | `wingman-backend`/`wingman-bot`, `APP_VERSION`, `ENVIRONMENT` |
| `event_type` | `log` (default), `http_request` (wide event) |
| `request_id`, `trace_id` | Inbound `x-request-id` or generated UUID; same value until tracing is adopted |
| Wide event only | `request_method`, `request_path`, `route`, `status_code`, `duration_ms`, `sample_reason` (`ERROR`/`SLOW`/`RANDOM`) |
| Errors only | `error_class`, `error_message` (redacted, truncated), `error_stack_hash` (hash, never full stack) |

Extra `extra={...}` fields are included unless the normalised field name
looks sensitive (token/secret/password/api-key/authorization/cookie/
credential/email/…), in which case the value is `[REDACTED]` — fail-closed.
Slack/OpenAI tokens, card numbers and emails in message text are scrubbed.

Example (ordinary log with structured extras):

```json
{"timestamp":"2026-08-18T01:23:45.123456+00:00","level":"INFO","service_name":"wingman-bot","environment":"development","service_version":"0.1.0","logger":"app.slack_bot","message":"Indexed file","event_type":"log","request_id":null,"trace_id":null,"file_type":"pdf"}
```

Extra fields appear at the top level. Exceptions use redacted error fields
and a stack hash, rather than a full traceback.

Not yet emitted (needs instrumentation, not just config): `user_id`/
`org_id` (hashed), `db_queries`, `external_calls`, `cache_hit`,
`retries_count`, resource usage. Do not claim these in assessments yet.

## Destinations and retention — current state

| Destination | Status | Retention |
|---|---|---|
| Container stdout (`compose.yaml`: backend, bot) | **Actual today** — collected only if the host captures it | Docker default json-file driver, no rotation configured in this repo |
| Local dev stdout | Actual | Terminal only, not retained |
| Any central sink (CloudWatch/Datadog/ELK/S3) | **Not configured** — no shipper, credentials, or IaC in this repo | None — cannot be evidenced |

Other Compose services are outside this Python schema: `frontend` emits
Next.js logs; `postgres` and `chroma` use their image defaults. No explicit
rotation or retention is configured for them in `compose.yaml` either.
The host's Docker daemon may override its default logging driver or rotation;
verify the deployed host before claiming a retention period. With Docker's
default `json-file` driver, logs grow without a size bound unless rotation is
configured, and local container logs do not survive container removal.

Assumed baseline to adopt (not yet in force): hot 7d, warm 30d,
cold 90d+ in a central sink, per the wide-event tiering model.
Until a sink is deployed, assessment evidence is limited to
`docker logs` output sampled at incident time.

## Controls / configuration

`LOG_LEVEL`, `LOG_FORMAT=json|text`, `ENVIRONMENT`,
`LOG_WIDE_EVENT_SAMPLE_RATE` (default `1.0`; errors and
`duration_ms > LOG_SLOW_MS` always kept), `LOG_SLOW_MS` — see
`.env.example`. Wide events use synchronous stdlib stream writes in the
request's finalizer. A slow stdout destination can delay request completion;
there is no background queue or log shipper in this baseline.

| Setting | Default | Purpose |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Minimum root logger level |
| `LOG_FORMAT` | `json` | JSON lines; `text` for local development |
| `ENVIRONMENT` | `development` | Environment label |
| `LOG_WIDE_EVENT_SAMPLE_RATE` | `1.0` | Fraction of ordinary HTTP requests logged |
| `LOG_SLOW_MS` | `1000` | Slow-request threshold in milliseconds |

### Application conventions

- Call `from app.logging import configure_logging` at process startup before
  importing application singletons. Use `configure_logging(service="wingman-backend")`
  in `app/main.py` and `configure_logging(service="wingman-bot")` in `run_bot.py`.
  Repeated calls replace the root handler rather than adding duplicate output.
- Library modules, including `app/slack_bot.py`, only obtain a logger with
  `logging.getLogger(__name__)`; they do not configure the process logger.
- Attach structured fields with `extra=`, for example
  `logger.info("Indexed file", extra={"file_type": "pdf"})`.
- Never log credentials or full Slack event/message payloads. Pattern redaction
  is a backstop, not proof that arbitrary user content is safe. Existing payload
  logging still needs review before claiming comprehensive sensitive-data controls.

## Needed for stronger assessment evidence

1. Deploy a log shipper/sink and configure rotation; record the real retention period.
2. Add OpenTelemetry tracing so `trace_id`/`span_id` are distinct from `request_id`.
3. Instrument DB/external-call counters and hashed user/org IDs into the wide event.
4. Alert/dashboard on error rate (`status_code>=500`) and p95 `duration_ms` by route.
5. Periodic access review and retention-deletion proof for the sink.
6. Review existing payload logging and add evidence that secrets and user content
   are excluded; document which operators can access each environment's logs.
