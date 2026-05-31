"""
Unit tests for Slack AI streaming functionality
"""
import pytest


class TestStreamingImports:
    """Test that streaming imports work correctly"""

    def test_import_markdown_text_chunk(self):
        """Test MarkdownTextChunk can be imported"""
        from slack_sdk.models.messages.chunk import MarkdownTextChunk
        assert MarkdownTextChunk is not None

    def test_import_task_update_chunk(self):
        """Test TaskUpdateChunk can be imported"""
        from slack_sdk.models.messages.chunk import TaskUpdateChunk
        assert TaskUpdateChunk is not None

    def test_import_plan_update_chunk(self):
        """Test PlanUpdateChunk can be imported"""
        from slack_sdk.models.messages.chunk import PlanUpdateChunk
        assert PlanUpdateChunk is not None


class TestStreamingChunks:
    """Test streaming chunk instantiation"""

    def test_markdown_text_chunk_creation(self):
        """Test creating a MarkdownTextChunk"""
        from slack_sdk.models.messages.chunk import MarkdownTextChunk

        chunk = MarkdownTextChunk(text="Hello, world!")
        assert chunk.text == "Hello, world!"
        assert chunk.type == "markdown_text"

    def test_markdown_text_chunk_with_markdown(self):
        """Test MarkdownTextChunk with markdown formatting"""
        from slack_sdk.models.messages.chunk import MarkdownTextChunk

        chunk = MarkdownTextChunk(text="**Bold** and *italic* text")
        assert "**Bold**" in chunk.text
        assert "*italic*" in chunk.text

    def test_task_update_chunk_pending(self):
        """Test creating a TaskUpdateChunk with pending status"""
        from slack_sdk.models.messages.chunk import TaskUpdateChunk

        chunk = TaskUpdateChunk(
            id="task-1",
            title="Searching knowledge base...",
            status="in_progress"
        )
        assert chunk.id == "task-1"
        assert chunk.title == "Searching knowledge base..."
        assert chunk.status == "in_progress"

    def test_task_update_chunk_complete(self):
        """Test creating a TaskUpdateChunk with complete status"""
        from slack_sdk.models.messages.chunk import TaskUpdateChunk

        chunk = TaskUpdateChunk(
            id="task-1",
            title="Searching knowledge base...",
            status="complete"
        )
        assert chunk.status == "complete"

    def test_task_update_chunk_with_details(self):
        """Test TaskUpdateChunk with details and output"""
        from slack_sdk.models.messages.chunk import TaskUpdateChunk

        chunk = TaskUpdateChunk(
            id="task-1",
            title="Searching...",
            status="complete",
            details="- Query executed\n- Results retrieved",
            output="Found 42 matching documents"
        )
        assert chunk.details is not None
        assert chunk.output is not None

    def test_plan_update_chunk(self):
        """Test creating a PlanUpdateChunk"""
        from slack_sdk.models.messages.chunk import PlanUpdateChunk

        chunk = PlanUpdateChunk(title="Processing your request...")
        assert chunk.title == "Processing your request..."

    def test_plan_update_chunk_empty_title(self):
        """Test PlanUpdateChunk with empty title"""
        from slack_sdk.models.messages.chunk import PlanUpdateChunk

        chunk = PlanUpdateChunk(title="")
        assert chunk.title == ""


class TestStreamingChunksToDict:
    """Test chunk serialization"""

    def test_markdown_text_chunk_to_dict(self):
        """Test MarkdownTextChunk serializes correctly"""
        from slack_sdk.models.messages.chunk import MarkdownTextChunk

        chunk = MarkdownTextChunk(text="Test message")
        result = chunk.to_dict()

        assert isinstance(result, dict)
        assert result.get("type") == "markdown_text"
        assert result.get("text") == "Test message"

    def test_task_update_chunk_to_dict(self):
        """Test TaskUpdateChunk serializes correctly"""
        from slack_sdk.models.messages.chunk import TaskUpdateChunk

        chunk = TaskUpdateChunk(
            id="task-1",
            title="Test task",
            status="in_progress"
        )
        result = chunk.to_dict()

        assert isinstance(result, dict)
        assert result.get("type") == "task_update"
        assert result.get("id") == "task-1"
        assert result.get("title") == "Test task"
        assert result.get("status") == "in_progress"

    def test_plan_update_chunk_to_dict(self):
        """Test PlanUpdateChunk serializes correctly"""
        from slack_sdk.models.messages.chunk import PlanUpdateChunk

        chunk = PlanUpdateChunk(title="Test plan")
        result = chunk.to_dict()

        assert isinstance(result, dict)
        assert result.get("type") == "plan_update"
        assert result.get("title") == "Test plan"


class TestStreamingHelper:
    """Test the chat_stream helper"""

    def test_chat_stream_helper_exists(self):
        """Test that chat_stream method exists on WebClient"""
        from slack_sdk import WebClient
        client = WebClient(token="xoxb-test")

        assert hasattr(client, 'chat_stream') or hasattr(client, 'chatStream')

    def test_chat_stream_returns_chat_stream_object(self):
        """Test chat_stream returns a ChatStream object"""
        from slack_sdk import WebClient
        client = WebClient(token="xoxb-test")

        if hasattr(client, 'chat_stream'):
            from slack_sdk.web.chat_stream import ChatStream
            streamer = client.chat_stream(
                channel="C12345",
                recipient_user_id="U12345",
                thread_ts="1234567890.123456",
            )
            assert isinstance(streamer, ChatStream)


class TestStreamingStatusValues:
    """Test valid status values for task chunks"""

    def test_valid_status_values(self):
        """Test that all valid status values work"""
        from slack_sdk.models.messages.chunk import TaskUpdateChunk

        valid_statuses = ["in_progress", "complete", "pending", "failed"]

        for status in valid_statuses:
            chunk = TaskUpdateChunk(
                id="test",
                title="Test",
                status=status
            )
            assert chunk.status == status

    def test_invalid_status_value(self):
        """Test that invalid status values are handled"""
        from slack_sdk.models.messages.chunk import TaskUpdateChunk

        chunk = TaskUpdateChunk(
            id="test",
            title="Test",
            status="invalid_status"
        )
        assert chunk.status == "invalid_status"


class TestStreamingIntegration:
    """Integration tests for streaming flow"""

    def test_streaming_flow_sequence(self):
        """Test the typical streaming flow creates correct chunk sequence"""
        from slack_sdk.models.messages.chunk import (
            PlanUpdateChunk,
            TaskUpdateChunk,
            MarkdownTextChunk
        )

        chunks = []

        chunks.append(PlanUpdateChunk(title="Processing your request..."))

        chunks.append(TaskUpdateChunk(
            id="thinking",
            title="Analyzing question...",
            status="in_progress"
        ))
        chunks.append(TaskUpdateChunk(
            id="thinking",
            title="Analyzing question...",
            status="complete"
        ))

        chunks.append(TaskUpdateChunk(
            id="searching",
            title="Searching knowledge base...",
            status="in_progress"
        ))
        chunks.append(TaskUpdateChunk(
            id="searching",
            title="Searching knowledge base...",
            status="complete"
        ))

        chunks.append(TaskUpdateChunk(
            id="generating",
            title="Generating response...",
            status="in_progress"
        ))
        chunks.append(TaskUpdateChunk(
            id="generating",
            title="Generating response...",
            status="complete"
        ))

        chunks.append(MarkdownTextChunk(text="Here's the answer..."))

        assert len(chunks) == 8
        assert isinstance(chunks[0], PlanUpdateChunk)
        assert isinstance(chunks[-1], MarkdownTextChunk)

        thinking_tasks = [c for c in chunks if getattr(c, 'id', None) == "thinking"]
        assert len(thinking_tasks) == 2
        assert thinking_tasks[0].status == "in_progress"
        assert thinking_tasks[1].status == "complete"

    def test_multiple_task_updates_same_id(self):
        """Test that same task ID can have multiple updates (status changes)"""
        from slack_sdk.models.messages.chunk import TaskUpdateChunk

        updates = [
            TaskUpdateChunk(id="task-1", title="Step 1", status="pending"),
            TaskUpdateChunk(id="task-1", title="Step 1", status="in_progress"),
            TaskUpdateChunk(id="task-1", title="Step 1", status="complete"),
        ]

        assert updates[0].status == "pending"
        assert updates[1].status == "in_progress"
        assert updates[2].status == "complete"

    def test_parallel_tasks(self):
        """Test that multiple tasks can run in parallel"""
        from slack_sdk.models.messages.chunk import TaskUpdateChunk

        tasks = [
            TaskUpdateChunk(id="task-1", title="Task A", status="in_progress"),
            TaskUpdateChunk(id="task-2", title="Task B", status="in_progress"),
            TaskUpdateChunk(id="task-3", title="Task C", status="pending"),
        ]

        assert tasks[0].id != tasks[1].id
        assert tasks[0].status == "in_progress"
        assert tasks[2].status == "pending"
