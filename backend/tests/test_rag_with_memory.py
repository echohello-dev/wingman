"""
Tests for RAG engine with conversation memory
"""
from datetime import datetime, timedelta

import pytest
from app.config import settings
from app.database import ConversationHistory, SessionLocal, init_db
from app.rag import rag_engine


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    init_db()
    session = SessionLocal()
    yield session
    session.query(ConversationHistory).delete()
    session.commit()
    session.close()


def test_store_conversation_turn(db):
    """Test storing a conversation turn"""
    conversation_id = "test:channel:user123"
    user_id = "user123"
    channel_id = "channel456"
    
    rag_engine._store_conversation_turn(
        conversation_id=conversation_id,
        user_id=user_id,
        channel_id=channel_id,
        role="user",
        message="What is the API?",
        message_ts="1234567890.123456"
    )
    
    # Verify it was stored
    db_entry = db.query(ConversationHistory).filter(
        ConversationHistory.conversation_id == conversation_id,
        ConversationHistory.role == "user"
    ).first()
    
    assert db_entry is not None
    assert db_entry.message == "What is the API?"
    assert db_entry.user_id == user_id
    assert db_entry.channel_id == channel_id


def test_store_assistant_response(db):
    """Test storing assistant response"""
    conversation_id = "test:channel:user123"
    
    rag_engine._store_conversation_turn(
        conversation_id=conversation_id,
        user_id="user123",
        channel_id="channel456",
        role="assistant",
        message="The API provides endpoints for asking questions and managing documents."
    )
    
    db_entry = db.query(ConversationHistory).filter(
        ConversationHistory.conversation_id == conversation_id,
        ConversationHistory.role == "assistant"
    ).first()
    
    assert db_entry is not None
    assert db_entry.role == "assistant"


def test_get_conversation_history_empty(db):
    """Test retrieving empty conversation history"""
    conversation_id = "nonexistent:conversation"
    history = rag_engine.get_conversation_history(conversation_id)
    
    assert history == ""


def test_get_conversation_history_formats_correctly(db):
    """Test conversation history is formatted correctly"""
    conversation_id = "test:conv"
    
    # Store a conversation
    rag_engine._store_conversation_turn(
        conversation_id=conversation_id,
        user_id="user123",
        channel_id="channel456",
        role="user",
        message="Hello"
    )
    
    rag_engine._store_conversation_turn(
        conversation_id=conversation_id,
        user_id="user123",
        channel_id="channel456",
        role="assistant",
        message="Hi there!"
    )
    
    history = rag_engine.get_conversation_history(conversation_id)
    
    assert "User: Hello" in history
    assert "Assistant: Hi there!" in history


def test_conversation_timeout_filtering(db):
    """Test that old conversations are filtered by timeout"""
    conversation_id = "test:timeout"
    
    # Store an old message (beyond timeout)
    old_message = ConversationHistory(
        conversation_id=conversation_id,
        user_id="user123",
        channel_id="channel456",
        role="user",
        message="Old message",
        created_at=datetime.utcnow() - timedelta(minutes=settings.CONVERSATION_TIMEOUT_MINUTES + 10)
    )
    
    # Store a recent message (within timeout)
    recent_message = ConversationHistory(
        conversation_id=conversation_id,
        user_id="user123",
        channel_id="channel456",
        role="user",
        message="Recent message",
        created_at=datetime.utcnow()
    )
    
    db.add(old_message)
    db.add(recent_message)
    db.commit()
    
    history = rag_engine.get_conversation_history(conversation_id)
    
    # Old message should not be in history
    assert "Old message" not in history
    # Recent message should be in history
    assert "Recent message" in history


def test_conversation_memory_window_limit(db):
    """Test that conversation history respects memory window limit"""
    conversation_id = "test:window"
    
    # Store more messages than the window size
    for i in range(settings.CONVERSATION_MEMORY_WINDOW + 5):
        message = ConversationHistory(
            conversation_id=conversation_id,
            user_id="user123",
            channel_id="channel456",
            role="user",
            message=f"Message {i}",
            created_at=datetime.utcnow() - timedelta(minutes=settings.CONVERSATION_MEMORY_WINDOW - i)
        )
        db.add(message)
    
    db.commit()
    
    history = rag_engine.get_conversation_history(conversation_id)
    
    # Count how many messages are in the history
    message_count = history.count("User: Message")
    
    # Should not exceed the window size
    assert message_count <= settings.CONVERSATION_MEMORY_WINDOW


def test_generate_response_stores_conversation(db):
    """Test that generate_response stores conversation turns"""
    conversation_id = "test:response"
    user_id = "user123"
    channel_id = "channel456"
    question = "What is RAG?"
    
    # Generate a response
    rag_engine.generate_response(
        question=question,
        channel_id=channel_id,
        conversation_id=conversation_id,
        user_id=user_id,
        message_ts="1234567890.123456"
    )
    
    # Verify both user message and assistant response are stored
    user_msg = db.query(ConversationHistory).filter(
        ConversationHistory.conversation_id == conversation_id,
        ConversationHistory.role == "user"
    ).first()
    
    assistant_msg = db.query(ConversationHistory).filter(
        ConversationHistory.conversation_id == conversation_id,
        ConversationHistory.role == "assistant"
    ).first()
    
    assert user_msg is not None
    assert user_msg.message == question
    assert assistant_msg is not None
    assert assistant_msg.role == "assistant"
