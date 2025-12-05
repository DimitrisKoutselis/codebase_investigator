"""
Unit tests for application layer DTOs.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.application.dtos.ingest_dtos import IngestRequest, IngestResponse, IngestStatus
from src.application.dtos.chat_dtos import ChatRequest, ChatResponse, MessageDTO
from src.application.dtos.session_dtos import SessionDTO, SessionListResponse


class TestIngestDTOs:
    """Tests for ingestion DTOs."""

    def test_ingest_request_valid_url(self):
        """Test IngestRequest with valid URL."""
        request = IngestRequest(repo_url="https://github.com/owner/repo")
        assert str(request.repo_url) == "https://github.com/owner/repo"

    def test_ingest_request_invalid_url(self):
        """Test IngestRequest with invalid URL."""
        with pytest.raises(ValidationError):
            IngestRequest(repo_url="not-a-url")

    def test_ingest_request_json_serialization(self):
        """Test IngestRequest JSON serialization."""
        request = IngestRequest(repo_url="https://github.com/owner/repo")
        json_data = request.model_dump()
        assert "repo_url" in json_data

    def test_ingest_status_enum(self):
        """Test IngestStatus enum values."""
        assert IngestStatus.PENDING == "pending"
        assert IngestStatus.IN_PROGRESS == "in_progress"
        assert IngestStatus.COMPLETED == "completed"
        assert IngestStatus.FAILED == "failed"

    def test_ingest_response_complete(self):
        """Test IngestResponse with all fields."""
        now = datetime.utcnow()
        response = IngestResponse(
            codebase_id="cb-123",
            repo_url="https://github.com/owner/repo",
            status=IngestStatus.COMPLETED,
            file_count=42,
            created_at=now,
            indexed_at=now,
        )

        assert response.codebase_id == "cb-123"
        assert response.repo_url == "https://github.com/owner/repo"
        assert response.status == IngestStatus.COMPLETED
        assert response.file_count == 42
        assert response.error_message is None

    def test_ingest_response_failed(self):
        """Test IngestResponse for failed ingestion."""
        response = IngestResponse(
            codebase_id="cb-123",
            repo_url="https://github.com/owner/repo",
            status=IngestStatus.FAILED,
            error_message="Clone failed",
            created_at=datetime.utcnow(),
        )

        assert response.status == IngestStatus.FAILED
        assert response.error_message == "Clone failed"
        assert response.file_count is None
        assert response.indexed_at is None

    def test_ingest_response_json_serialization(self):
        """Test IngestResponse JSON serialization."""
        response = IngestResponse(
            codebase_id="cb-123",
            repo_url="https://github.com/owner/repo",
            status=IngestStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        json_data = response.model_dump()

        assert json_data["codebase_id"] == "cb-123"
        assert json_data["status"] == "pending"


class TestChatDTOs:
    """Tests for chat DTOs."""

    def test_message_dto_creation(self):
        """Test MessageDTO creation."""
        dto = MessageDTO(
            role="user",
            content="Hello!",
            timestamp=datetime.utcnow(),
        )

        assert dto.role == "user"
        assert dto.content == "Hello!"
        assert dto.metadata is None

    def test_message_dto_with_metadata(self):
        """Test MessageDTO with metadata."""
        dto = MessageDTO(
            role="assistant",
            content="Here's the answer.",
            timestamp=datetime.utcnow(),
            metadata={"sources": ["file1.py"]},
        )

        assert dto.metadata == {"sources": ["file1.py"]}

    def test_chat_request_simple(self):
        """Test ChatRequest with message only."""
        request = ChatRequest(message="What does this code do?")

        assert request.message == "What does this code do?"
        assert request.stream is False

    def test_chat_request_with_stream(self):
        """Test ChatRequest with stream flag."""
        request = ChatRequest(message="Explain this", stream=True)

        assert request.stream is True

    def test_chat_request_empty_message(self):
        """Test ChatRequest allows empty message (validation depends on business logic)."""
        request = ChatRequest(message="")
        assert request.message == ""

    def test_chat_response_creation(self):
        """Test ChatResponse creation."""
        now = datetime.utcnow()
        response = ChatResponse(
            session_id="sess-123",
            message=MessageDTO(
                role="assistant",
                content="The code does...",
                timestamp=now,
            ),
            sources=["src/main.py", "src/utils.py"],
        )

        assert response.session_id == "sess-123"
        assert response.message.role == "assistant"
        assert response.sources == ["src/main.py", "src/utils.py"]

    def test_chat_response_no_sources(self):
        """Test ChatResponse without sources."""
        response = ChatResponse(
            session_id="sess-123",
            message=MessageDTO(
                role="assistant",
                content="General answer",
                timestamp=datetime.utcnow(),
            ),
        )

        assert response.sources is None

    def test_chat_response_json_serialization(self):
        """Test ChatResponse JSON serialization."""
        response = ChatResponse(
            session_id="sess-123",
            message=MessageDTO(
                role="assistant",
                content="Answer",
                timestamp=datetime.utcnow(),
            ),
            sources=["file.py"],
        )
        json_data = response.model_dump()

        assert json_data["session_id"] == "sess-123"
        assert json_data["message"]["role"] == "assistant"
        assert json_data["sources"] == ["file.py"]


class TestSessionDTOs:
    """Tests for session DTOs."""

    def test_session_dto_creation(self):
        """Test SessionDTO creation."""
        now = datetime.utcnow()
        dto = SessionDTO(
            id="sess-123",
            codebase_id="cb-456",
            message_count=5,
            created_at=now,
            updated_at=now,
        )

        assert dto.id == "sess-123"
        assert dto.codebase_id == "cb-456"
        assert dto.message_count == 5
        assert dto.title is None
        assert dto.messages is None

    def test_session_dto_with_title(self):
        """Test SessionDTO with title."""
        dto = SessionDTO(
            id="sess-123",
            codebase_id="cb-456",
            title="Question about main.py",
            message_count=2,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert dto.title == "Question about main.py"

    def test_session_dto_with_messages(self):
        """Test SessionDTO with messages."""
        now = datetime.utcnow()
        messages = [
            MessageDTO(role="user", content="Question", timestamp=now),
            MessageDTO(role="assistant", content="Answer", timestamp=now),
        ]
        dto = SessionDTO(
            id="sess-123",
            codebase_id="cb-456",
            message_count=2,
            created_at=now,
            updated_at=now,
            messages=messages,
        )

        assert len(dto.messages) == 2
        assert dto.messages[0].role == "user"

    def test_session_list_response(self):
        """Test SessionListResponse creation."""
        now = datetime.utcnow()
        sessions = [
            SessionDTO(
                id=f"sess-{i}",
                codebase_id="cb-456",
                message_count=i,
                created_at=now,
                updated_at=now,
            )
            for i in range(3)
        ]

        response = SessionListResponse(sessions=sessions, total=3)

        assert len(response.sessions) == 3
        assert response.total == 3

    def test_session_list_response_empty(self):
        """Test SessionListResponse with no sessions."""
        response = SessionListResponse(sessions=[], total=0)

        assert response.sessions == []
        assert response.total == 0

    def test_session_dto_json_serialization(self):
        """Test SessionDTO JSON serialization."""
        now = datetime.utcnow()
        dto = SessionDTO(
            id="sess-123",
            codebase_id="cb-456",
            title="Test",
            message_count=1,
            created_at=now,
            updated_at=now,
        )
        json_data = dto.model_dump()

        assert json_data["id"] == "sess-123"
        assert json_data["codebase_id"] == "cb-456"
        assert json_data["title"] == "Test"
