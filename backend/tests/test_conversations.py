"""Tests for the conversation list and detail endpoints."""
import os

os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-stub")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-signing-secret")

from datetime import datetime, timedelta

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, ConversationHistory, get_db

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


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app, raise_server_exceptions=False)

BASE_TIME = datetime(2026, 1, 1, 9, 0, 0)


def _turn(conversation_id, channel_id, role, message, minutes, user_id="U1"):
    return ConversationHistory(
        conversation_id=conversation_id,
        user_id=user_id,
        channel_id=channel_id,
        role=role,
        message=message,
        created_at=BASE_TIME + timedelta(minutes=minutes),
    )


@pytest.fixture(autouse=True)
def seed():
    db = TestingSession()
    db.query(ConversationHistory).delete()
    db.commit()
    db.add_all([
        _turn("conv-a", "C1", "user", "How do I reset VPN?", 0),
        _turn("conv-a", "C1", "assistant", "Use the IT portal.", 1),
        _turn("conv-a", "C1", "user", "Thanks, that worked.", 5),
        _turn("conv-b", "C2", "user", "When is the office open?", 2),
        _turn("conv-b", "C2", "assistant", "Nine to five.", 3),
        _turn("conv-c", "C1", "user", "x" * 200, 10),
    ])
    db.commit()
    db.close()
    yield
    db = TestingSession()
    db.query(ConversationHistory).delete()
    db.commit()
    db.close()


class TestListConversations:
    def test_lists_summaries_most_recent_first(self):
        response = client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert [item["conversation_id"] for item in data["items"]] == [
            "conv-c", "conv-a", "conv-b",
        ]
        first = data["items"][0]
        assert first["channel_id"] == "C1"
        assert first["message_count"] == 1
        assert first["last_message_preview"] == "x" * 120

    def test_summary_counts_and_preview(self):
        response = client.get("/api/conversations")
        by_id = {i["conversation_id"]: i for i in response.json()["items"]}
        assert by_id["conv-a"]["message_count"] == 3
        assert by_id["conv-a"]["last_message_preview"] == "Thanks, that worked."
        assert by_id["conv-a"]["first_message_at"] is not None
        assert by_id["conv-a"]["last_message_at"] is not None

    def test_pagination(self):
        page_one = client.get("/api/conversations?limit=2&offset=0").json()
        page_two = client.get("/api/conversations?limit=2&offset=2").json()
        assert page_one["total"] == 3
        assert len(page_one["items"]) == 2
        assert len(page_two["items"]) == 1
        assert page_one["items"][0]["conversation_id"] != page_two["items"][0]["conversation_id"]

    def test_channel_filter(self):
        data = client.get("/api/conversations?channel_id=C2").json()
        assert data["total"] == 1
        assert data["items"][0]["conversation_id"] == "conv-b"

    @pytest.mark.parametrize("channel_id", ["C1", "C2"])
    def test_channel_filter_scopes_preview_for_shared_conversation(self, channel_id):
        other_channel = "C2" if channel_id == "C1" else "C1"
        with TestingSession() as db:
            db.add_all([
                _turn("shared", channel_id, "user", "Question in requested channel", 20),
                _turn("shared", channel_id, "assistant", "Answer in requested channel", 21),
                _turn("shared", other_channel, "assistant", "Answer in another channel", 30),
            ])
            db.commit()

        response = client.get("/api/conversations", params={"channel_id": channel_id})
        assert response.status_code == 200
        summary = response.json()["items"][0]
        assert summary == {
            "conversation_id": "shared",
            "channel_id": channel_id,
            "message_count": 2,
            "first_message_at": (BASE_TIME + timedelta(minutes=20)).isoformat(),
            "last_message_at": (BASE_TIME + timedelta(minutes=21)).isoformat(),
            "last_message_preview": "Answer in requested channel",
        }

    def test_unfiltered_preview_includes_latest_turn_across_channels(self):
        with TestingSession() as db:
            db.add_all([
                _turn("shared", "C1", "user", "Earlier question", 20),
                _turn("shared", "C2", "assistant", "Latest answer", 30),
            ])
            db.commit()

        response = client.get("/api/conversations")
        assert response.status_code == 200
        summary = response.json()["items"][0]
        assert summary["conversation_id"] == "shared"
        assert summary["message_count"] == 2
        assert summary["last_message_preview"] == "Latest answer"

    def test_scoped_preview_breaks_timestamp_ties_by_latest_id(self):
        with TestingSession() as db:
            db.add(_turn("shared", "C1", "user", "Question", 20))
            db.flush()
            db.add(_turn("shared", "C1", "assistant", "Answer", 20))
            db.flush()
            db.add(_turn("shared", "C2", "assistant", "Other channel answer", 20))
            db.commit()

        response = client.get("/api/conversations?channel_id=C1")
        assert response.status_code == 200
        summary = response.json()["items"][0]
        assert summary["conversation_id"] == "shared"
        assert summary["message_count"] == 2
        assert summary["last_message_preview"] == "Answer"

    def test_invalid_pagination_rejected(self):
        assert client.get("/api/conversations?limit=0").status_code == 422
        assert client.get("/api/conversations?limit=201").status_code == 422
        assert client.get("/api/conversations?offset=-1").status_code == 422

    def test_empty_database(self):
        db = TestingSession()
        db.query(ConversationHistory).delete()
        db.commit()
        db.close()
        data = client.get("/api/conversations").json()
        assert data == {"items": [], "total": 0, "limit": 50, "offset": 0}


class TestConversationDetail:
    def test_returns_turns_in_chronological_order(self):
        response = client.get("/api/conversations/conv-a")
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "conv-a"
        assert data["total"] == 3
        assert [item["message"] for item in data["items"]] == [
            "How do I reset VPN?",
            "Use the IT portal.",
            "Thanks, that worked.",
        ]
        assert [item["role"] for item in data["items"]] == ["user", "assistant", "user"]

    def test_detail_pagination(self):
        data = client.get("/api/conversations/conv-a?limit=1&offset=1").json()
        assert data["total"] == 3
        assert len(data["items"]) == 1
        assert data["items"][0]["message"] == "Use the IT portal."

    def test_missing_conversation_is_404(self):
        response = client.get("/api/conversations/does-not-exist")
        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found"

    def test_detail_invalid_pagination_rejected(self):
        assert client.get("/api/conversations/conv-a?limit=0").status_code == 422
