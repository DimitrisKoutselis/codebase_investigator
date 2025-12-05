"""
Unit tests for domain entities.
"""

import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time

from src.domain.entities.message import Message, MessageRole
from src.domain.entities.chat_session import ChatSession
from src.domain.entities.codebase import Codebase, IndexingStatus
from src.domain.value_objects.session_id import SessionId
from src.domain.value_objects.repo_url import RepoURL


class TestMessage:
    """Tests for Message entity."""

    def test_user_message_creation(self):
        """Test creating a user message."""
        message = Message.user_message("Hello, how are you?")

        assert message.role == MessageRole.USER
        assert message.content == "Hello, how are you?"
        assert message.metadata is None
        assert isinstance(message.timestamp, datetime)

    def test_assistant_message_creation(self):
        """Test creating an assistant message."""
        message = Message.assistant_message("I'm doing well!")

        assert message.role == MessageRole.ASSISTANT
        assert message.content == "I'm doing well!"
        assert message.metadata is None

    def test_assistant_message_with_metadata(self):
        """Test creating an assistant message with metadata."""
        metadata = {"sources": ["file1.py", "file2.py"], "confidence": 0.95}
        message = Message.assistant_message("Here's the answer.", metadata=metadata)

        assert message.metadata == metadata
        assert message.metadata["sources"] == ["file1.py", "file2.py"]

    def test_message_immutability(self):
        """Test that Message is immutable (frozen dataclass)."""
        message = Message.user_message("Test")

        with pytest.raises(AttributeError):
            message.content = "Modified"

    def test_message_roles_enum(self):
        """Test all message roles exist."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"

    def test_direct_message_creation(self):
        """Test creating message directly."""
        now = datetime.utcnow()
        message = Message(
            role=MessageRole.SYSTEM,
            content="System prompt",
            timestamp=now,
            metadata={"key": "value"},
        )

        assert message.role == MessageRole.SYSTEM
        assert message.content == "System prompt"
        assert message.timestamp == now
        assert message.metadata == {"key": "value"}

    @freeze_time("2024-01-15 10:30:00")
    def test_user_message_timestamp(self):
        """Test that timestamp is set correctly."""
        message = Message.user_message("Test")
        assert message.timestamp == datetime(2024, 1, 15, 10, 30, 0)


class TestChatSession:
    """Tests for ChatSession entity."""

    @pytest.fixture
    def session(self) -> ChatSession:
        """Create a fresh session for each test."""
        return ChatSession(
            id=SessionId.generate(),
            codebase_id="test-codebase-123",
        )

    def test_session_creation(self, session: ChatSession):
        """Test session creation with defaults."""
        assert session.codebase_id == "test-codebase-123"
        assert session.messages == []
        assert session.title is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_add_message(self, session: ChatSession):
        """Test adding a message to session."""
        message = Message.user_message("Hello")
        initial_updated_at = session.updated_at

        session.add_message(message)

        assert len(session.messages) == 1
        assert session.messages[0] == message
        assert session.updated_at >= initial_updated_at

    def test_add_multiple_messages(self, session: ChatSession):
        """Test adding multiple messages."""
        session.add_message(Message.user_message("Question 1"))
        session.add_message(Message.assistant_message("Answer 1"))
        session.add_message(Message.user_message("Question 2"))

        assert len(session.messages) == 3

    def test_title_auto_generation_from_first_user_message(self, session: ChatSession):
        """Test title is auto-generated from first user message."""
        session.add_message(Message.user_message("What does this function do?"))

        assert session.title == "What does this function do?"

    def test_title_truncation_for_long_message(self, session: ChatSession):
        """Test title is truncated for long messages."""
        long_message = "A" * 100  # 100 characters
        session.add_message(Message.user_message(long_message))

        assert session.title == "A" * 50 + "..."
        assert len(session.title) == 53

    def test_title_not_changed_after_first_user_message(self, session: ChatSession):
        """Test title is not changed after first user message."""
        session.add_message(Message.user_message("First question"))
        session.add_message(Message.user_message("Second question"))

        assert session.title == "First question"

    def test_title_not_set_from_assistant_message(self, session: ChatSession):
        """Test title is not set from assistant message."""
        session.add_message(Message.assistant_message("Hello!"))

        assert session.title is None

    def test_get_conversation_history(self, session: ChatSession):
        """Test getting conversation history in LLM format."""
        session.add_message(Message.user_message("Question"))
        session.add_message(Message.assistant_message("Answer"))

        history = session.get_conversation_history()

        assert history == [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

    def test_get_conversation_history_empty(self, session: ChatSession):
        """Test getting conversation history when empty."""
        assert session.get_conversation_history() == []

    def test_message_count_property(self, session: ChatSession):
        """Test message_count property."""
        assert session.message_count == 0

        session.add_message(Message.user_message("One"))
        assert session.message_count == 1

        session.add_message(Message.assistant_message("Two"))
        assert session.message_count == 2

    def test_session_with_custom_timestamps(self):
        """Test session with custom timestamps."""
        custom_time = datetime(2024, 1, 15, 10, 30)
        session = ChatSession(
            id=SessionId.generate(),
            codebase_id="test",
            created_at=custom_time,
            updated_at=custom_time,
        )

        assert session.created_at == custom_time
        assert session.updated_at == custom_time


class TestCodebase:
    """Tests for Codebase entity."""

    @pytest.fixture
    def codebase(self) -> Codebase:
        """Create a fresh codebase for each test."""
        return Codebase(
            id="cb-123",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/cb-123",
        )

    def test_codebase_creation(self, codebase: Codebase):
        """Test codebase creation with defaults."""
        assert codebase.id == "cb-123"
        assert codebase.repo_url.value == "https://github.com/owner/repo"
        assert codebase.local_path == "./repos/cb-123"
        assert codebase.indexing_status == IndexingStatus.PENDING
        assert codebase.indexed_at is None
        assert codebase.file_count == 0
        assert codebase.error_message is None
        assert isinstance(codebase.created_at, datetime)

    def test_mark_indexing_started(self, codebase: Codebase):
        """Test marking indexing as started."""
        codebase.mark_indexing_started()

        assert codebase.indexing_status == IndexingStatus.IN_PROGRESS

    def test_mark_indexing_completed(self, codebase: Codebase):
        """Test marking indexing as completed."""
        codebase.mark_indexing_started()
        codebase.mark_indexing_completed(file_count=42)

        assert codebase.indexing_status == IndexingStatus.COMPLETED
        assert codebase.file_count == 42
        assert codebase.indexed_at is not None
        assert isinstance(codebase.indexed_at, datetime)

    def test_mark_indexing_failed(self, codebase: Codebase):
        """Test marking indexing as failed."""
        codebase.mark_indexing_started()
        codebase.mark_indexing_failed("Clone failed: repository not found")

        assert codebase.indexing_status == IndexingStatus.FAILED
        assert codebase.error_message == "Clone failed: repository not found"

    def test_is_ready_when_pending(self, codebase: Codebase):
        """Test is_ready returns False when pending."""
        assert codebase.is_ready is False

    def test_is_ready_when_in_progress(self, codebase: Codebase):
        """Test is_ready returns False when in progress."""
        codebase.mark_indexing_started()
        assert codebase.is_ready is False

    def test_is_ready_when_completed(self, codebase: Codebase):
        """Test is_ready returns True when completed."""
        codebase.mark_indexing_completed(10)
        assert codebase.is_ready is True

    def test_is_ready_when_failed(self, codebase: Codebase):
        """Test is_ready returns False when failed."""
        codebase.mark_indexing_failed("Error")
        assert codebase.is_ready is False

    def test_indexing_status_enum_values(self):
        """Test all indexing status values."""
        assert IndexingStatus.PENDING.value == "pending"
        assert IndexingStatus.IN_PROGRESS.value == "in_progress"
        assert IndexingStatus.COMPLETED.value == "completed"
        assert IndexingStatus.FAILED.value == "failed"

    def test_full_lifecycle(self, codebase: Codebase):
        """Test full indexing lifecycle."""
        # Initial state
        assert codebase.indexing_status == IndexingStatus.PENDING
        assert not codebase.is_ready

        # Start indexing
        codebase.mark_indexing_started()
        assert codebase.indexing_status == IndexingStatus.IN_PROGRESS
        assert not codebase.is_ready

        # Complete indexing
        codebase.mark_indexing_completed(100)
        assert codebase.indexing_status == IndexingStatus.COMPLETED
        assert codebase.is_ready
        assert codebase.file_count == 100
        assert codebase.indexed_at is not None

    def test_codebase_with_custom_created_at(self):
        """Test codebase with custom created_at."""
        custom_time = datetime(2024, 1, 15)
        codebase = Codebase(
            id="test",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./test",
            created_at=custom_time,
        )

        assert codebase.created_at == custom_time
