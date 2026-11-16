"""Saved-document indexing with SQLite, local Chroma and fixed embeddings."""
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
from app.database import Base, Document, get_db
from app.vector_store import VectorStore
import app.rag as rag_module

with patch("slack_sdk.WebClient.auth_test", return_value={
    "ok": True, "bot_id": "BTEST", "user_id": "UTEST", "team_id": "TTEST",
}):
    from app.main import app


CONTENT = "Reset VPN via IT portal."
QUESTION = "How do I reset VPN?"


class DocumentEmbeddings(Embeddings):
    def embed_documents(self, texts):
        # The full guide has distance 1, shorter fragments have larger distances.
        return [[float(len(CONTENT) - len(text) + 1), 1.0] for text in texts]

    def embed_query(self, text):
        return [0.0, 1.0]


@pytest.fixture
def document_api(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    sessions = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    def get_test_db():
        with sessions() as db:
            yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = get_test_db
    monkeypatch.setattr(Posthog, "capture", lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, "RETRIEVAL_TOP_K", 5)
    monkeypatch.setattr(settings, "RETRIEVAL_MAX_DISTANCE", None)
    monkeypatch.setattr(settings, "CHUNK_SIZE", 1000)
    monkeypatch.setattr(settings, "CHUNK_OVERLAP", 0)
    vector = VectorStore()
    vector.vector_store = Chroma(
        client=chromadb.PersistentClient(
            path=str(tmp_path), settings=ChromaSettings(anonymized_telemetry=False),
        ),
        collection_name="saved-document-fixture", embedding_function=DocumentEmbeddings(),
    )
    vector._initialized = True
    monkeypatch.setattr(rag_module, "vector_store", vector)
    monkeypatch.setattr("app.main.vector_store", vector)
    blocked = Mock(side_effect=AssertionError("Document indexing must not contact Slack or generate"))
    monkeypatch.setattr("slack_sdk.WebClient.api_call", blocked)
    monkeypatch.setattr("slack_bolt.adapter.socket_mode.SocketModeHandler.start", blocked)
    monkeypatch.setattr(rag_module.agent_runtime, "generate", blocked)
    monkeypatch.setattr(rag_module.agent_runtime, "submit", blocked)
    try:
        yield TestClient(app, raise_server_exceptions=False), sessions, vector
        blocked.assert_not_called()
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
        engine.dispose()


def create_document(client, content=CONTENT):
    return client.post("/api/documents", json={"title": "VPN guide", "content": content})


def retry_index(client, document_id):
    return client.post(f"/api/documents/{document_id}/index")


def test_create_and_retry_keep_one_owned_chunk_and_preserve_saved_record(document_api):
    client, sessions, vector = document_api
    response = create_document(client)
    assert response.status_code == 200
    document_id = response.json()["id"]
    original = client.get(f"/api/documents/{document_id}").json()
    for _ in range(2):
        response = retry_index(client, document_id)
        assert response.status_code == 200
        assert response.json() == {"id": document_id, "message": "Document indexed successfully"}
    assert vector.vector_store.get()["ids"] == [f"document:{document_id}:0"]
    assert vector.similarity_search(QUESTION) == [{
        "content": CONTENT, "distance": 1.0,
        "metadata": {"title": "VPN guide", "source": "api", "chunk": 0, "document_id": document_id},
    }]
    assert client.get(f"/api/documents/{document_id}").json() == original
    with sessions() as db:
        assert db.query(Document).count() == 1


def test_retry_recovers_saved_document_after_embedding_failure_with_transcript(document_api):
    client, sessions, vector = document_api
    with patch.object(vector.vector_store._embedding_function, "embed_documents",
                      side_effect=RuntimeError("Private provider credentials")):
        failed = create_document(client)
    assert failed.status_code == 503
    document_id = failed.json()["detail"]["document_id"]
    assert failed.json() == {"detail": {
        "message": "Document saved but indexing is unavailable", "document_id": document_id,
    }}
    assert "Private" not in failed.text
    assert client.get(f"/api/documents/{document_id}").json()["content"] == CONTENT
    before = vector.similarity_search(QUESTION)
    assert before == []
    for _ in range(2):
        assert retry_index(client, document_id).status_code == 200
    after = vector.similarity_search(QUESTION)
    assert [item["content"] for item in after] == [CONTENT]
    assert [item["distance"] for item in after] == [1.0]
    with sessions() as db:
        assert db.query(Document).count() == 1
    print(json.dumps({
        "query": QUESTION, "document_id": document_id, "top_k": 5,
        "before_retry": before, "after_two_retries": after,
        "chunk_count": vector.vector_store._collection.count(),
        "note": "Fixed-vector squared L2 distances prove recovery and identity, not production relevance.",
    }, indent=2))


def test_retry_rechunks_and_removes_only_obsolete_owned_chunks(document_api, monkeypatch):
    client, _, vector = document_api
    monkeypatch.setattr(settings, "CHUNK_SIZE", 8)
    document_id = create_document(client).json()["id"]
    assert len(vector.vector_store.get(where={"document_id": document_id})["ids"]) == 3
    other_id = create_document(client).json()["id"]  # Same title and source, distinct owner.
    legacy_ids = vector.add_documents([CONTENT], [{"title": "VPN guide", "source": "api"}])
    slack_ids = vector.add_documents([CONTENT], [{"source": "slack", "channel_id": "CTEST"}])
    other_before = vector.vector_store.get(where={"document_id": other_id})
    monkeypatch.setattr(settings, "CHUNK_SIZE", 1000)
    for _ in range(2):
        assert retry_index(client, document_id).status_code == 200
    owned = vector.vector_store.get(where={"document_id": document_id})
    assert owned["ids"] == [f"document:{document_id}:0"]
    assert owned["documents"] == [CONTENT]
    assert vector.vector_store.get(where={"document_id": other_id}) == other_before
    assert set(vector.vector_store.get()["ids"]) == {
        *owned["ids"], *other_before["ids"], *legacy_ids, *slack_ids,
    }


def test_retry_reads_latest_saved_content_title_and_source(document_api):
    client, sessions, vector = document_api
    document_id = create_document(client).json()["id"]
    updated_content = "Ask IT for access."
    with sessions() as db:
        db.query(Document).filter(Document.id == document_id).update({
            "title": "VPN handbook", "content": updated_content, "source": "docs",
        })
        db.commit()
    assert retry_index(client, document_id).status_code == 200
    assert vector.vector_store.get()["ids"] == [f"document:{document_id}:0"]
    assert vector.similarity_search(QUESTION) == [{
        "content": updated_content,
        "distance": float(len(CONTENT) - len(updated_content) + 1) ** 2,
        "metadata": {"title": "VPN handbook", "source": "docs", "chunk": 0, "document_id": document_id},
    }]


@pytest.mark.parametrize("stage", ["lookup", "embed", "upsert"])
def test_retry_failure_keeps_previous_chunks_and_saved_content(document_api, monkeypatch, stage):
    client, _, vector = document_api
    monkeypatch.setattr(settings, "CHUNK_SIZE", 8)
    document_id = create_document(client).json()["id"]
    before = vector.vector_store.get(include=["documents", "metadatas", "embeddings"])
    saved = client.get(f"/api/documents/{document_id}").json()
    monkeypatch.setattr(settings, "CHUNK_SIZE", 1000)
    if stage == "lookup":
        target, method = vector.vector_store, "get"
    elif stage == "embed":
        target, method = vector.vector_store._embedding_function, "embed_documents"
    else:
        target, method = vector.vector_store._collection, "upsert"
    with patch.object(target, method, side_effect=RuntimeError("Private provider details")):
        failed = retry_index(client, document_id)
    assert failed.status_code == 503
    assert "Private" not in failed.text
    after = vector.vector_store.get(include=["documents", "metadatas", "embeddings"])
    assert after["documents"] == before["documents"]
    assert after["metadatas"] == before["metadatas"]
    assert after["embeddings"].tolist() == before["embeddings"].tolist()
    assert client.get(f"/api/documents/{document_id}").json() == saved
    assert retry_index(client, document_id).status_code == 200
    assert vector.vector_store.get()["documents"] == [CONTENT]


def test_cleanup_failure_is_reported_and_retry_finishes_without_duplicates(document_api, monkeypatch):
    client, _, vector = document_api
    monkeypatch.setattr(settings, "CHUNK_SIZE", 8)
    document_id = create_document(client).json()["id"]
    monkeypatch.setattr(settings, "CHUNK_SIZE", 1000)
    with patch.object(vector.vector_store, "delete", side_effect=RuntimeError("Cleanup unavailable")):
        assert retry_index(client, document_id).status_code == 503
    assert len(vector.vector_store.get()["ids"]) == 3
    assert retry_index(client, document_id).status_code == 200
    assert vector.vector_store.get()["ids"] == [f"document:{document_id}:0"]
    assert vector.vector_store.get()["documents"] == [CONTENT]


def test_missing_saved_document_does_not_initialise_vector_store(document_api, monkeypatch):
    client, _, vector = document_api
    index = Mock(side_effect=AssertionError("Missing document must not be indexed"))
    monkeypatch.setattr(vector, "replace_document", index)
    response = retry_index(client, 999)
    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}
    index.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("content", " \n\t "), ("content", None), ("title", ""), ("source", None),
])
def test_invalid_legacy_document_is_rejected_without_changing_chunks(document_api, monkeypatch, field, value):
    client, sessions, vector = document_api
    document_id = create_document(client).json()["id"]
    with sessions() as db:
        db.query(Document).filter(Document.id == document_id).update({field: value})
        db.commit()
    index = Mock(side_effect=AssertionError("Invalid document must not be indexed"))
    monkeypatch.setattr(vector, "replace_document", index)
    response = retry_index(client, document_id)
    assert response.status_code == 422
    assert response.json() == {"detail": "Saved document has invalid title, content or source"}
    index.assert_not_called()
    assert vector.vector_store.get()["documents"] == [CONTENT]
