"""Structured (JSON) wide-event logging baseline. Stdlib only.

Schema, destinations and retention: see docs/logging.md.
One wide event per HTTP request (``event_type="http_request"``) plus
ordinary structured logs for exceptions/lifecycle. Sensitive values are
redacted fail-closed: any field whose normalised name looks sensitive
is dropped, and known secret/PII patterns are scrubbed from strings.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import random
import re
import sys
import time
import uuid
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)

_SENSITIVE = ("token", "secret", "password", "passwd", "apikey", "authorization",
              "cookie", "credential", "privatekey", "sessionid", "email")
_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
]
REDACTED = "[REDACTED]"
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime", "taskName"}


def _is_sensitive(key: str) -> bool:
    norm = re.sub(r"[^a-z0-9]", "", key.lower())
    return any(s in norm for s in _SENSITIVE)


def redact(value):
    """Redact by field meaning; unknown string content is pattern-scrubbed."""
    if isinstance(value, dict):
        return {k: (REDACTED if _is_sensitive(str(k)) else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        out = value
        for p in _PATTERNS:
            out = p.sub(REDACTED, out)
        return out[:2000]
    return value


def hash_value(value: str | None) -> str | None:
    return None if not value else hashlib.sha256(value.encode()).hexdigest()[:16]


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str = "wingman-backend", environment: str = "development", version: str = "0.1.0"):
        super().__init__()
        self.service, self.environment, self.version = service, environment, version

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "service_name": self.service,
            "environment": self.environment,
            "service_version": self.version,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "event_type": getattr(record, "event_type", "log"),
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
            "trace_id": getattr(record, "trace_id", None) or trace_id_var.get(),
        }
        for k, v in record.__dict__.items():
            if k not in _RESERVED and k not in payload and not k.startswith("_"):
                payload[k] = REDACTED if _is_sensitive(k) else redact(v)
        if record.exc_info and record.exc_info[0]:
            exc = record.exc_info[1]
            payload["error_class"] = record.exc_info[0].__name__
            payload["error_message"] = redact(str(exc)) if exc else None
            payload["error_stack_hash"] = hash_value("".join(
                line.rsplit(":", 1)[0] for line in self.formatException(record.exc_info).splitlines()))
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", fmt: str = "json", service: str = "wingman-backend",
                      environment: str = "development", version: str = "0.1.0") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service, environment, version) if fmt.lower() == "json"
                         else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())


class WideEventMiddleware:
    """Pure-ASGI: emits one wide event per HTTP request, non-blocking."""

    def __init__(self, app, logger_name="wingman.wide_event", sample_rate: float = 1.0, slow_ms: float = 1000):
        self.app, self.sample_rate, self.slow_ms = app, sample_rate, slow_ms
        self.log = logging.getLogger(logger_name)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        rid = next((v.decode() for k, v in scope.get("headers", []) if k == b"x-request-id"), None) or uuid.uuid4().hex
        tokens = (request_id_var.set(rid), trace_id_var.set(rid))
        start, status, error = time.perf_counter(), 500, None

        async def wrapped(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, wrapped)
        except Exception as exc:  # record, then preserve framework handling
            error = exc
            raise
        finally:
            duration = round((time.perf_counter() - start) * 1000, 2)
            keep = error is not None or status >= 500 or duration > self.slow_ms or random.random() < self.sample_rate
            if keep:
                self.log.info("http_request", extra={
                    "event_type": "http_request", "request_id": rid, "trace_id": rid,
                    "request_method": scope.get("method"), "request_path": scope.get("path"),
                    "route": scope.get("path"), "status_code": status, "duration_ms": duration,
                    "error_class": type(error).__name__ if error else None,
                    "error_message": redact(str(error)) if error else None,
                    "sample_reason": "ERROR" if (error or status >= 500) else "SLOW" if duration > self.slow_ms else "RANDOM",
                })
            request_id_var.reset(tokens[0]); trace_id_var.reset(tokens[1])
