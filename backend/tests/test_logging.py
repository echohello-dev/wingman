"""Check process logging setup without changing pytest's own handlers."""

import json
import os
import subprocess
import sys
from datetime import datetime

import pytest


def run_logging(code, **settings):
    return subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, **settings},
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.mark.parametrize("service", ["wingman-backend", "wingman-bot"])
def test_json_stdout_preserves_controls_and_avoids_duplicate_handlers(service):
    result = run_logging(
        f"""
import logging
from app.logging import configure_logging
from app.logging_config import request_id_var
configure_logging(service={service!r})
configure_logging(service={service!r})
request_id_var.set("smoke-123")
logger = logging.getLogger("logging.smoke")
logger.debug("filtered")
logger.info("Indexed %s", "file", extra={{"file_type": "pdf", "api_token": "secret"}})
try:
    raise ValueError("contact me@example.org")
except ValueError:
    logger.exception("Index failed")
""",
        LOG_FORMAT="json", LOG_LEVEL="INFO", ENVIRONMENT="test", APP_VERSION="1.2.3",
    )
    records = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(records) == 2
    info, error = records
    assert info["service_name"] == service
    assert info["environment"] == "test" and info["service_version"] == "1.2.3"
    assert datetime.fromisoformat(info["timestamp"]).utcoffset().total_seconds() == 0
    assert info["message"] == "Indexed file" and info["file_type"] == "pdf"
    assert info["request_id"] == "smoke-123" and info["api_token"] == "[REDACTED]"
    assert error["level"] == "ERROR" and error["error_class"] == "ValueError"
    assert error["error_message"] == "contact [REDACTED]"
    assert error["error_stack_hash"] and "exception" not in error
    assert not result.stderr


def test_text_format_and_configured_level():
    result = run_logging(
        """
import logging
from app.logging import configure_logging
configure_logging()
logger = logging.getLogger("logging.smoke")
logger.info("filtered")
logger.warning("visible")
""",
        LOG_FORMAT="text", LOG_LEVEL="WARNING",
    )
    assert len(result.stdout.splitlines()) == 1
    assert "WARNING logging.smoke visible" in result.stdout
    assert not result.stderr


def test_api_keeps_backend_service_when_importing_bot():
    result = run_logging(
        """
import sys
from types import ModuleType
from unittest.mock import patch
from fastapi.testclient import TestClient

# The health endpoint does not use RAG or Slack; keep this check offline.
rag = ModuleType("app.rag")
rag.rag_engine = object()
sys.modules["app.rag"] = rag
with patch("slack_sdk.WebClient.auth_test", return_value={
    "ok": True, "bot_id": "BTEST", "user_id": "UTEST", "team_id": "TTEST"
}):
    from app.main import app
response = TestClient(app).get("/health", headers={"x-request-id": "health-smoke"})
assert response.status_code == 200
""",
        LOG_FORMAT="json", LOG_LEVEL="INFO", DATABASE_URL="sqlite://",
        SLACK_BOT_TOKEN="xoxb-test", SLACK_SIGNING_SECRET="test",
    )
    records = [json.loads(line) for line in result.stdout.splitlines()]
    events = [record for record in records if record["event_type"] == "http_request"]
    assert len(events) == 1
    event = events[0]
    assert event["service_name"] == "wingman-backend"
    assert event["request_id"] == "health-smoke" and event["status_code"] == 200
    assert event["duration_ms"] >= 0
