"""Runtime boundary tests without external services or model credentials."""
from unittest.mock import Mock
import importlib.util
from pathlib import Path
import sys
import types

import httpx
import pytest

from app import agent_runtime


def test_transport_retry_keeps_request_id(monkeypatch):
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    response = Mock()
    response.json.return_value = {"id": "job-1", "status": "pending"}
    client.post.side_effect = [httpx.ReadTimeout("Lost acknowledgement"), response]
    monkeypatch.setattr(httpx, "Client", Mock(return_value=client))
    monkeypatch.setattr(agent_runtime.time, "sleep", lambda _: None)
    payload = {"request_id": "same-event"}
    assert agent_runtime.submit(payload)["id"] == "job-1"
    assert client.post.call_count == 2
    assert all(call.kwargs["json"] == payload for call in client.post.call_args_list)


def test_rag_routes_retrieved_context_and_stable_slack_identity(monkeypatch):
    vector = Mock()
    vector.similarity_search.return_value = [
        {"content": "Correct channel", "metadata": {"channel_id": "C1", "source": "slack"}},
        {"content": "Other channel", "metadata": {"channel_id": "C2", "source": "slack"}},
    ]
    monkeypatch.setitem(sys.modules, "app.vector_store", types.SimpleNamespace(vector_store=vector))
    spec = importlib.util.spec_from_file_location("rag_under_test", Path(__file__).parents[1] / "app/rag.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    submit = Mock(return_value={"id": "job-1", "status": "pending"})
    monkeypatch.setattr(agent_runtime, "submit", submit)
    module.rag_engine.submit_slack("Question", "C1", "team:thread:C1:1.2", "event-1", "1.2")
    payload = submit.call_args.args[0]
    assert payload["request_id"] == "event-1"
    assert payload["conversation_id"] == "team:thread:C1:1.2"
    assert "Correct channel" in payload["context"]
    assert "Other channel" not in payload["context"]
    assert payload["slack"] == {"channel": "C1", "thread_ts": "1.2"}


def test_failed_job_surfaces_error(monkeypatch):
    monkeypatch.setattr(agent_runtime, "submit", lambda _: {"id": "job-1"})
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.get.return_value.json.return_value = {"status": "failed", "error": "Model unavailable"}
    monkeypatch.setattr(httpx, "Client", Mock(return_value=client))
    with pytest.raises(RuntimeError, match="Model unavailable"):
        agent_runtime.generate({})
