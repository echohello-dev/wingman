"""Offline tests for document creation, listing and detail endpoints."""
import os

os.environ.setdefault("SLACK_BOT_TOKEN", "[REDACTED]")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-signing-secret")

from datetime import datetime, timedelta

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, Document, get_db
from app.rag import rag_engine

with patch("slack_sdk.WebClient.auth_test", return_value={
    "ok": True, "bot_id": "BTEST", "user_id": "UTEST", "team_id": "TTEST"
}):
    from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def use_document_db():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous

BASE_TIME = datetime(2026, 1, 1, 9, 0, 0)


def _doc(title, content, source, minutes):
    return Document(
        title=title,
        content=content,
        source=source,
        created_at=BASE_TIME + timedelta(minutes=minutes),
        updated_at=BASE_TIME + timedelta(minutes=minutes),
    )


@pytest.fixture(autouse=True)
def seed():
    db = TestingSession()
    db.query(Document).delete()
    db.commit()
    db.add_all([
        _doc("VPN guide", "Use the IT portal to reset VPN.", "api", 0),
        _doc("Office hours", "Nine to five.", "docs", 2),
        _doc("Long guide", "x" * 200, "api", 10),
    ])
    db.commit()
    seeded_ids = [doc.id for doc in db.query(Document).order_by(Document.id).all()]
    db.close()
    yield seeded_ids
    db = TestingSession()
    db.query(Document).delete()
    db.commit()
    db.close()


class TestListDocuments:
    def test_lists_documents_most_recent_first(self):
        response = client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert [item["title"] for item in data["items"]] == [
            "Long guide", "Office hours", "VPN guide",
        ]
        first = data["items"][0]
        assert first["source"] == "api"
        assert first["content_preview"] == "x" * 120

    def test_preview_and_fields(self):
        data = client.get("/api/documents").json()
        by_title = {i["title"]: i for i in data["items"]}
        assert by_title["VPN guide"]["content_preview"] == "Use the IT portal to reset VPN."
        assert by_title["VPN guide"]["created_at"] is not None
        assert "content" not in by_title["VPN guide"]

    def test_pagination(self):
        page_one = client.get("/api/documents?limit=2&offset=0").json()
        page_two = client.get("/api/documents?limit=2&offset=2").json()
        assert page_one["total"] == 3
        assert len(page_one["items"]) == 2
        assert len(page_two["items"]) == 1
        assert page_one["items"][0]["id"] != page_two["items"][0]["id"]

    def test_source_filter(self):
        data = client.get("/api/documents?source=docs").json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Office hours"

    def test_invalid_pagination_rejected(self):
        assert client.get("/api/documents?limit=0").status_code == 422
        assert client.get("/api/documents?limit=201").status_code == 422
        assert client.get("/api/documents?offset=-1").status_code == 422

    def test_empty_database(self):
        db = TestingSession()
        db.query(Document).delete()
        db.commit()
        db.close()
        data = client.get("/api/documents").json()
        assert data == {"items": [], "total": 0, "limit": 50, "offset": 0}


class TestDocumentDetail:
    def test_returns_full_content(self, seed):
        doc_id = seed[0]
        response = client.get(f"/api/documents/{doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert data["title"] == "VPN guide"
        assert data["content"] == "Use the IT portal to reset VPN."
        assert data["source"] == "api"
        assert data["created_at"] is not None

    def test_missing_document_is_404(self):
        response = client.get("/api/documents/999999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"


class TestCreateDocument:
    @pytest.mark.parametrize("field", ["title", "content", "source"])
    @pytest.mark.parametrize("value", ["", " \n\t ", "\u2003\u00a0", None, 123])
    def test_rejects_invalid_fields_without_writes_or_indexing(self, field, value):
        payload = {"title": "VPN guide", "content": "Reset via IT.", "source": "api"}
        payload[field] = value
        with patch.object(rag_engine, "index_document") as index:
            response = client.post("/api/documents", json=payload)
        assert response.status_code == 422
        assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
        index.assert_not_called()
        with TestingSession() as db:
            assert db.query(Document).count() == 3

    @pytest.mark.parametrize("field", ["title", "content"])
    def test_rejects_missing_required_fields(self, field):
        payload = {"title": "VPN guide", "content": "Reset via IT."}
        del payload[field]
        with patch.object(rag_engine, "index_document") as index:
            response = client.post("/api/documents", json=payload)
        assert response.status_code == 422
        index.assert_not_called()
        with TestingSession() as db:
            assert db.query(Document).count() == 3

    @pytest.mark.parametrize("source", [None, " \tdocs\n "])
    def test_creates_readable_document_and_indexes_preserved_content(self, source):
        content = "\n    def reset_vpn():\n        return 'IT portal'\n\n"
        payload = {"title": " \tVPN guide\n ", "content": content}
        if source is not None:
            payload["source"] = source
        expected_source = "api" if source is None else "docs"
        with patch.object(rag_engine, "index_document") as index:
            response = client.post("/api/documents", json=payload)
        assert response.status_code == 200
        index.assert_called_once_with("VPN guide", content, expected_source)
        document_id = response.json()["id"]
        detail = client.get(f"/api/documents/{document_id}").json()
        assert detail["title"] == "VPN guide"
        assert detail["content"] == content
        assert detail["source"] == expected_source
        with TestingSession() as db:
            assert db.query(Document).count() == 4
