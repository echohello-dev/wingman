"""Retrieval preview API tests with local Chroma and fixed embeddings."""
import json
import os
from unittest.mock import Mock, patch

os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-fixture-only")
os.environ.setdefault("SLACK_SIGNING_SECRET", "fixture-only")

import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings
from chromadb.telemetry.product.posthog import Posthog
from fastapi.testclient import TestClient
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings

from app.config import settings
from app.vector_store import VectorStore

with patch("slack_sdk.WebClient.auth_test", return_value={
    "ok": True, "bot_id": "BTEST", "user_id": "UTEST", "team_id": "TTEST",
}):
    import app.main as main


QUESTION = "How do I reset VPN?"


class PreviewEmbeddings(Embeddings):
    def embed_documents(self, texts):
        positions = {
            "Other channel guide": 0.0,
            "Shared guide": 0.5,
            "Reset VPN via IT portal": 1.0,
            "Ask IT for VPN access": 2.0,
        }
        return [[positions[text], 1.0] for text in texts]

    def embed_query(self, text):
        return [0.0, 1.0]


@pytest.fixture
def preview_api(tmp_path, monkeypatch):
    monkeypatch.setattr(Posthog, "capture", lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, "RETRIEVAL_TOP_K", 2)
    monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", None)
    store = VectorStore()
    store.vector_store = Chroma(
        client=chromadb.PersistentClient(
            path=str(tmp_path), settings=ChromaSettings(anonymized_telemetry=False),
        ),
        collection_name="preview-fixture", embedding_function=PreviewEmbeddings(),
    )
    store._initialized = True
    store.add_documents(
        ["Other channel guide", "Shared guide", "Reset VPN via IT portal", "Ask IT for VPN access"],
        [{"source": "slack", "channel_id": "COTHER"},
         {"source": "docs", "title": "Shared guide"},
         {"source": "slack", "channel_id": "CTARGET", "message_ts": "1.0"},
         {"source": "slack", "channel_id": "CTARGET", "message_ts": "2.0"}],
    )
    monkeypatch.setattr(main, "vector_store", store)
    blocked = Mock(side_effect=AssertionError("Preview must not generate or contact Slack"))
    for method in ("generate_response", "submit_slack", "match_operator_rule"):
        monkeypatch.setattr(main.rag_engine, method, blocked)
    monkeypatch.setattr("slack_sdk.WebClient.api_call", blocked)
    monkeypatch.setattr("slack_bolt.adapter.socket_mode.SocketModeHandler.start", blocked)
    yield TestClient(main.app, raise_server_exceptions=False), store
    blocked.assert_not_called()


def preview(client, **options):
    return client.post("/api/retrieval/preview", json={"question": QUESTION, **options})


def test_preview_returns_ranked_chunks_metadata_distances_and_settings(preview_api):
    client, store = preview_api
    response = preview(client)
    assert response.status_code == 200
    assert response.json() == {
        "question": QUESTION, "channel_id": None, "top_k": 2, "max_distance": None,
        "items": store.similarity_search(QUESTION),
    }
    assert [item["content"] for item in response.json()["items"]] == [
        "Other channel guide", "Shared guide",
    ]
    assert [item["distance"] for item in response.json()["items"]] == [0.0, 0.25]


def test_preview_applies_channel_scope_before_top_k(preview_api):
    client, _ = preview_api
    data = preview(client, channel_id="CTARGET").json()
    assert data["channel_id"] == "CTARGET"
    assert data["items"] == [
        {"content": "Reset VPN via IT portal", "distance": 1.0,
         "metadata": {"source": "slack", "channel_id": "CTARGET", "message_ts": "1.0"}},
        {"content": "Ask IT for VPN access", "distance": 4.0,
         "metadata": {"source": "slack", "channel_id": "CTARGET", "message_ts": "2.0"}},
    ]


def test_preview_exposes_inclusive_distance_cutoff_with_transcript(preview_api, monkeypatch):
    client, store = preview_api
    before = preview(client, channel_id="CTARGET").json()
    monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", 1.0)
    response = preview(client, channel_id="CTARGET")
    assert response.status_code == 200
    after = response.json()
    assert after["max_distance"] == 1.0
    assert after["items"] == before["items"][:1]
    assert after["items"] == store.similarity_search(QUESTION, channel_id="CTARGET")
    print(json.dumps({
        "before_cutoff": before, "after_cutoff": after,
        "note": "Fixed-vector squared L2 distances prove policy parity, not production relevance."
    }, indent=2))


@pytest.mark.parametrize("empty_reason", ["collection", "channel", "cutoff"])
def test_preview_returns_success_for_empty_results(preview_api, monkeypatch, empty_reason):
    client, store = preview_api
    channel = "CTARGET"
    if empty_reason == "collection":
        ids = store.vector_store.get()["ids"]
        store.vector_store.delete(ids=ids)
    elif empty_reason == "channel":
        channel = "CMISSING"
    else:
        monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", 0.0)
    response = preview(client, channel_id=channel)
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.parametrize("payload", [
    {}, {"question": ""}, {"question": " \n\t "}, {"question": None}, {"question": 123},
    {"question": QUESTION, "channel_id": ""},
    {"question": QUESTION, "channel_id": " \t "},
])
def test_preview_rejects_invalid_input_before_search(preview_api, monkeypatch, payload):
    client, store = preview_api
    search = Mock(side_effect=AssertionError("Invalid input must not reach retrieval"))
    monkeypatch.setattr(store, "similarity_search", search)
    response = client.post("/api/retrieval/preview", json=payload)
    assert response.status_code == 422
    search.assert_not_called()


def test_preview_trims_question_and_channel(preview_api):
    client, _ = preview_api
    response = client.post("/api/retrieval/preview", json={
        "question": f"  {QUESTION}\n", "channel_id": " CTARGET ",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == QUESTION
    assert data["channel_id"] == "CTARGET"
    assert len(data["items"]) == 2


def test_preview_reports_unavailable_retrieval_without_exposing_error(preview_api, monkeypatch):
    client, store = preview_api
    monkeypatch.setattr(store, "similarity_search", Mock(side_effect=RuntimeError(
        "Private connection details must not appear in the response",
    )))
    response = preview(client)
    assert response.status_code == 503
    assert response.json() == {"detail": "Retrieval is unavailable"}
