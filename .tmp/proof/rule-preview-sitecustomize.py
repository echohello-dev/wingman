"""Offline proof hook: fixture Slack authentication and deny external work."""
from slack_sdk import WebClient
from slack_bolt.adapter.socket_mode import SocketModeHandler


def blocked(*args, **kwargs):
    raise AssertionError("Slack, retrieval and Pi calls are forbidden in this proof")


WebClient.auth_test = lambda *args, **kwargs: {
    "ok": True, "bot_id": "BTEST", "user_id": "UTEST", "team_id": "TTEST",
}
WebClient.api_call = blocked
SocketModeHandler.start = blocked

from app import agent_runtime
from app.vector_store import vector_store

agent_runtime.generate = blocked
agent_runtime.submit = blocked
vector_store.similarity_search = blocked
