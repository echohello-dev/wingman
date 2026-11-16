"""Document removal with SQLite, local Chroma, and no external services."""
import json
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Document
from app.vector_store import VectorStore
from tests.test_document_indexing import (
    CONTENT, QUESTION, create_document, document_api,
)


def test_delete_removes_only_owned_chunks_with_retrieval_transcript(document_api, monkeypatch):
    client, _, vector = document_api
    monkeypatch.setattr(settings, "CHUNK_SIZE", 8)
    monkeypatch.setattr(settings, "RETRIEVAL_TOP_K", 20)
    document_id = create_document(client).json()["id"]
    other_id = create_document(client).json()["id"]  # Identical title, source and content.
    legacy_ids = vector.add_documents([CONTENT], [{"title": "VPN guide", "source": "api"}])
    slack_ids = vector.add_documents([CONTENT], [{"source": "slack", "channel_id": "CTEST"}])
    before = vector.similarity_search(QUESTION)
    preserved_ids = [f"document:{other_id}:{i}" for i in range(3)] + legacy_ids + slack_ids
    preserved = vector.vector_store.get(
        ids=preserved_ids, include=["documents", "metadatas", "embeddings"],
    )
    assert len(before) == 8
    assert len([item for item in before if item["metadata"].get("document_id") == document_id]) == 3

    response = client.delete(f"/api/documents/{document_id}")
    assert response.status_code == 200
    assert response.json() == {"id": document_id, "message": "Document deleted successfully"}
    after = vector.similarity_search(QUESTION)
    assert len(after) == 5
    assert all(item["metadata"].get("document_id") != document_id for item in after)
    assert {item["distance"] for item in before} == {1.0, 289.0}
    assert {item["distance"] for item in after} == {1.0, 289.0}
    remaining = vector.vector_store.get(include=["documents", "metadatas", "embeddings"])
    assert remaining["ids"] == preserved["ids"]
    assert remaining["documents"] == preserved["documents"]
    assert remaining["metadatas"] == preserved["metadatas"]
    assert remaining["embeddings"].tolist() == preserved["embeddings"].tolist()
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert client.post(f"/api/documents/{document_id}/index").status_code == 404
    assert [item["id"] for item in client.get("/api/documents").json()["items"]] == [other_id]
    assert client.delete(f"/api/documents/{document_id}").status_code == 404
    print(json.dumps({
        "query": QUESTION, "deleted_document_id": document_id, "top_k": 20,
        "before_delete": before, "after_delete": after,
        "note": "Fixed-vector squared L2 distances demonstrate ownership removal, not production relevance.",
    }, indent=2))


@pytest.mark.parametrize("document_id,status", [(999, 404), (-1, 404), ("invalid", 422), ("1.5", 422)])
def test_missing_or_invalid_delete_does_not_initialise_vector_store(document_api, monkeypatch, document_id, status):
    client, _, vector = document_api
    initialise = Mock(side_effect=AssertionError("Missing document must not access Chroma"))
    monkeypatch.setattr(vector, "_ensure_initialized", initialise)
    response = client.delete(f"/api/documents/{document_id}")
    assert response.status_code == status
    if status == 404:
        assert response.json() == {"detail": "Document not found"}
    initialise.assert_not_called()


def test_delete_unindexed_legacy_record_needs_no_valid_content_or_embeddings(document_api):
    client, sessions, vector = document_api
    with sessions() as db:
        doc = Document(title=None, content=None, source=None)
        db.add(doc)
        db.commit()
        document_id = doc.id
    with patch.object(vector.vector_store._embedding_function, "embed_documents",
                      side_effect=AssertionError("Deletion must not embed")), \
         patch.object(vector.vector_store._embedding_function, "embed_query",
                      side_effect=AssertionError("Deletion must not embed")):
        assert client.delete(f"/api/documents/{document_id}").status_code == 200
    assert client.get("/api/documents").json()["total"] == 0
    assert vector.vector_store.get()["ids"] == []


@pytest.mark.parametrize("stage", ["initialise", "delete", "lost-acknowledgement"])
def test_vector_delete_failure_retains_saved_record_and_allows_retry(document_api, stage):
    client, _, vector = document_api
    document_id = create_document(client).json()["id"]
    saved = client.get(f"/api/documents/{document_id}").json()
    original_delete = vector.vector_store.delete

    def fail_after_deleting(*args, **kwargs):
        original_delete(*args, **kwargs)
        raise RuntimeError("Private Chroma credentials")

    target, method = (vector, "_ensure_initialized") if stage == "initialise" else (vector.vector_store, "delete")
    failure = fail_after_deleting if stage == "lost-acknowledgement" else RuntimeError("Private Chroma credentials")
    with patch.object(target, method, side_effect=failure):
        response = client.delete(f"/api/documents/{document_id}")
    assert response.status_code == 503
    assert response.json() == {"detail": {
        "message": "Document deletion is unavailable", "document_id": document_id,
    }}
    assert "Private" not in response.text
    assert client.get(f"/api/documents/{document_id}").json() == saved
    expected = [] if stage == "lost-acknowledgement" else [CONTENT]
    assert vector.vector_store.get()["documents"] == expected
    assert client.delete(f"/api/documents/{document_id}").status_code == 200
    assert vector.vector_store.get()["ids"] == []
    assert client.get(f"/api/documents/{document_id}").status_code == 404


@pytest.mark.parametrize("method", ["delete", "commit"])
def test_database_delete_failure_rolls_back_saved_record_and_can_retry(document_api, method):
    client, _, vector = document_api
    document_id = create_document(client).json()["id"]
    saved = client.get(f"/api/documents/{document_id}").json()
    with patch.object(Session, method, side_effect=RuntimeError("Private database credentials")):
        response = client.delete(f"/api/documents/{document_id}")
    assert response.status_code == 503
    assert response.json() == {"detail": {
        "message": "Document deletion is unavailable", "document_id": document_id,
    }}
    assert "Private" not in response.text
    assert client.get(f"/api/documents/{document_id}").json() == saved
    assert vector.vector_store.get()["ids"] == []  # Separate stores are not atomic.
    assert client.delete(f"/api/documents/{document_id}").status_code == 200
    assert client.get(f"/api/documents/{document_id}").status_code == 404


def test_delete_still_requires_an_initialised_adapter(monkeypatch):
    vector = VectorStore()
    monkeypatch.setattr(vector, "_ensure_initialized", lambda: None)
    with pytest.raises(RuntimeError, match="Vector store not initialized"):
        vector.delete_document(1)
