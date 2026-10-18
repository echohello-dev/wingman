# Structured logging baseline (Wingman #7)

## Schema

All services emit one JSON object per line to **stdout** via
`backend/app/logging_config.py` (`JsonFormatter`, `configure_logging`).

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

Not yet emitted (needs instrumentation, not just config): `user_id`/
`org_id` (hashed), `db_queries`, `external_calls`, `cache_hit`,
`retries_count`, resource usage. Do not claim these in assessments yet.

## Destinations and retention — current state

| Destination | Status | Retention |
|---|---|---|
| Container stdout (`compose.yaml`: backend, bot) | **Actual today** — collected only if the host captures it | Docker default json-file driver, no rotation configured in this repo |
| Local dev stdout | Actual | Terminal only, not retained |
| Any central sink (CloudWatch/Datadog/ELK/S3) | **Not configured** — no shipper, credentials, or IaC in this repo | None — cannot be evidenced |

Assumed baseline to adopt (not yet in force): hot 7d, warm 30d,
cold 90d+ in a central sink, per the wide-event tiering model.
Until a sink is deployed, assessment evidence is limited to
`docker logs` output sampled at incident time.

## Controls / configuration

`LOG_LEVEL`, `LOG_FORMAT=json|text`, `ENVIRONMENT`,
`LOG_WIDE_EVENT_SAMPLE_RATE` (default `1.0`; errors and
`duration_ms > LOG_SLOW_MS` always kept), `LOG_SLOW_MS` — see
`.env.example`. Wide events are emitted fire-and-forget on the logging
handler; they never block the response beyond stdlib stream write.

## Needed for stronger assessment evidence

1. Deploy a log shipper/sink and configure rotation; record the real retention period.
2. Add OpenTelemetry tracing so `trace_id`/`span_id` are distinct from `request_id`.
3. Instrument DB/external-call counters and hashed user/org IDs into the wide event.
4. Alert/dashboard on error rate (`status_code>=500`) and p95 `duration_ms` by route.
5. Periodic access review and retention-deletion proof for the sink.
