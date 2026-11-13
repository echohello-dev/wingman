"""Saved-thread API regressions with SQLite, local Chroma and fixed embeddings."""
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, SlackMessage, get_db
from app.vector_store import VectorStore

with patch("slack_sdk.WebClient.auth_test", return_value={
    "ok": True, "bot_id": "BTEST", "user_id": "UTEST", "team_id": "TTEST",
}):
    from app.main import app

import app.rag as rag_module


ROOT_TS = "1700000000.000001"
REPLY_TS = "1700000001.000001"
LAST_TS = "1700000002.000001"


def message(ts, text, thread_ts=None, channel="CTARGET"):
    return SlackMessage(
        message_ts=ts, channel_id=channel, user_id="UTEST", text=text,
        thread_ts=thread_ts,
    )


@pytest.fixture
def saved_thread_api(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    sessions = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    with sessions() as db:
        # Insert out of timestamp order, with unrelated rows in both channels.
        db.add_all([
            message(LAST_TS, "Check the VPN guide", ROOT_TS),
            message(ROOT_TS, "How do I reset VPN?"),
            message(REPLY_TS, "Use the IT portal", ROOT_TS),
            message("1700000003.000001", "Unrelated thread", "1700000099.000001"),
            message("1700000004.000001", "Other channel reply", ROOT_TS, "COTHER"),
        ])
        db.commit()

    def get_test_db():
        with sessions() as db:
            yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = get_test_db
    index = Mock()
    monkeypatch.setattr(rag_module.rag_engine, "index_slack_thread", index)
    try:
        yield TestClient(app, raise_server_exceptions=False), sessions, index
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
        engine.dispose()


def index_request(client, channel="CTARGET", thread_ts=ROOT_TS):
    return client.post("/api/index/thread", params={
        "channel_id": channel, "thread_ts": thread_ts,
    })


def test_saved_thread_includes_root_and_replies_in_timestamp_order(saved_thread_api):
    client, _, index = saved_thread_api
    response = index_request(client)
    assert response.status_code == 200
    assert response.json() == {"message": "Indexed 3 messages", "thread_ts": ROOT_TS}
    index.assert_called_once_with([
        {"text": "How do I reset VPN?", "ts": ROOT_TS, "user": "UTEST", "thread_ts": None},
        {"text": "Use the IT portal", "ts": REPLY_TS, "user": "UTEST", "thread_ts": ROOT_TS},
        {"text": "Check the VPN guide", "ts": LAST_TS, "user": "UTEST", "thread_ts": ROOT_TS},
    ], "CTARGET")


@pytest.mark.parametrize("root_thread_ts", [None, ROOT_TS])
def test_saved_root_only_thread_is_indexed_once(saved_thread_api, root_thread_ts):
    client, sessions, index = saved_thread_api
    with sessions() as db:
        db.query(SlackMessage).filter(SlackMessage.message_ts != ROOT_TS).delete()
        db.query(SlackMessage).update({SlackMessage.thread_ts: root_thread_ts})
        db.commit()
    response = index_request(client)
    assert response.status_code == 200
    assert response.json()["message"] == "Indexed 1 messages"
    assert [item["ts"] for item in index.call_args.args[0]] == [ROOT_TS]


def test_saved_replies_can_be_indexed_without_a_saved_root(saved_thread_api):
    client, sessions, index = saved_thread_api
    with sessions() as db:
        db.query(SlackMessage).filter(SlackMessage.message_ts == ROOT_TS).delete()
        db.commit()
    assert index_request(client).status_code == 200
    assert [item["ts"] for item in index.call_args.args[0]] == [REPLY_TS, LAST_TS]


@pytest.mark.parametrize("channel,thread_ts", [
    ("CTARGET", "1700000098.000001"), ("CEMPTY", ROOT_TS),
])
def test_missing_saved_thread_returns_404_without_indexing(saved_thread_api, channel, thread_ts):
    client, _, index = saved_thread_api
    response = index_request(client, channel, thread_ts)
    assert response.status_code == 404
    assert response.json() == {"detail": "Thread not found"}
    index.assert_not_called()


def test_saved_thread_channel_filter_also_applies_to_root_lookup(saved_thread_api):
    client, _, index = saved_thread_api
    response = index_request(client, "COTHER")
    assert response.status_code == 200
    index.assert_called_once_with([
        {"text": "Other channel reply", "ts": "1700000004.000001", "user": "UTEST",
         "thread_ts": ROOT_TS},
    ], "COTHER")


def test_saved_thread_indexing_failure_remains_500(saved_thread_api):
    client, _, index = saved_thread_api
    index.side_effect = RuntimeError("Fixture indexing failure")
    response = index_request(client)
    assert response.status_code == 500
    assert response.json() == {"detail": "Fixture indexing failure"}


class ThreadEmbeddings(Embeddings):
    def embed_documents(self, texts):
        positions = {"How do I reset VPN?": 0.0, "Use the IT portal": 1.0, "Check the VPN guide": 2.0}
        return [[positions[text], 1.0] for text in texts]

    def embed_query(self, text):
        return [0.0, 1.0]


def test_saved_thread_retrieval_includes_original_question(saved_thread_api, tmp_path, monkeypatch):
    client, sessions, index = saved_thread_api
    monkeypatch.setattr(Posthog, "capture", lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, "RETRIEVAL_TOP_K", 5)
    monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", None)
    vector = VectorStore()
    vector.vector_store = Chroma(
        client=chromadb.PersistentClient(
            path=str(tmp_path), settings=ChromaSettings(anonymized_telemetry=False),
        ),
        collection_name="saved-thread-fixture", embedding_function=ThreadEmbeddings(),
    )
    vector._initialized = True
    monkeypatch.setattr(rag_module, "vector_store", vector)
    # Call the shared engine's real indexer through the API-boundary spy.
    index.side_effect = rag_module.RAGEngine.index_slack_thread.__get__(rag_module.rag_engine)
    query = "How do I reset VPN?"
    with sessions() as db:
        legacy = db.query(SlackMessage).filter(
            SlackMessage.channel_id == "CTARGET", SlackMessage.thread_ts == ROOT_TS,
        ).all()
        rag_module.rag_engine.index_slack_thread([
            {"text": row.text, "ts": row.message_ts, "thread_ts": row.thread_ts}
            for row in legacy
        ], "CTARGET")
    before = vector.similarity_search(query, channel_id="CTARGET")
    assert [row["content"] for row in before] == ["Use the IT portal", "Check the VPN guide"]
    for _ in range(2):
        assert index_request(client).status_code == 200
    after = vector.similarity_search(query, channel_id="CTARGET")
    assert [row["content"] for row in after] == [
        "How do I reset VPN?", "Use the IT portal", "Check the VPN guide",
    ]
    assert [row["distance"] for row in before] == [1.0, 4.0]
    assert [row["distance"] for row in after] == [0.0, 1.0, 4.0]
    assert vector.vector_store._collection.count() == 3
    print(json.dumps({"query": query, "channel_id": "CTARGET", "top_k": 5,
                      "before": before, "after": after}, indent=2))
