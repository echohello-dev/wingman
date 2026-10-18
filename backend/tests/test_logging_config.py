import json, logging
import pytest
from app.logging_config import JsonFormatter, WideEventMiddleware, redact

def fmt_record(msg="hi %s", args=("x",), **extra):
    r = logging.LogRecord("t", logging.INFO, __file__, 1, msg, args, None)
    for k, v in extra.items(): setattr(r, k, v)
    return json.loads(JsonFormatter().format(r))

def test_json_schema_and_redaction_variants():
    out = fmt_record(api_token="abc", slack_bot_token="xoxb-1", note="mail a@b.com xoxb-secret")
    assert out["service_name"] and out["timestamp"] and out["level"] == "INFO"
    assert out["api_token"] == "[REDACTED]" and out["slack_bot_token"] == "[REDACTED]"
    assert "a@b.com" not in out["message"] and "xoxb-secret" not in out["message"]
    assert redact("contact me@example.org") == "contact [REDACTED]"
    # unenumerated long-form variant must not pass through
    assert redact({"client_secret_value": "s"})["client_secret_value"] == "[REDACTED]"

def test_error_hash_not_stack():
    try: raise ValueError("bad a@b.com")
    except ValueError:
        import sys; r = logging.LogRecord("t", logging.ERROR, __file__, 1, "fail", (), sys.exc_info())
    out = json.loads(JsonFormatter().format(r))
    assert out["error_class"] == "ValueError" and out["error_stack_hash"] and "a@b.com" not in out["error_message"]

@pytest.mark.asyncio
async def test_wide_event_one_per_request(caplog):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})
    async def send(m): pass
    with caplog.at_level(logging.INFO, logger="wingman.wide_event"):
        await WideEventMiddleware(app)({"type": "http", "method": "GET", "path": "/health", "headers": []}, None, send)
    events = [json.loads(r.message) if False else r for r in caplog.records if r.name == "wingman.wide_event"]
    assert len(events) == 1 and events[0].event_type == "http_request" and events[0].status_code == 200
