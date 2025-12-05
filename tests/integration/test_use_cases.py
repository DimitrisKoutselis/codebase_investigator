"""
Integration tests for application use cases.

These tests verify that use cases work correctly with mocked infrastructure.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from src.application.use_cases.ingest_codebase import IngestCodebaseUseCase
from src.application.use_cases.send_message import SendMessageUseCase
from src.application.use_cases.get_session import GetSessionUseCase
from src.application.dtos.ingest_dtos import IngestRequest, IngestStatus
from src.application.dtos.chat_dtos import ChatRequest
from src.application.interfaces.i_vector_store import CodeChunk
from src.domain.entities.codebase import Codebase, IndexingStatus
from src.domain.entities.chat_session import ChatSession
from src.domain.entities.message import Message
from src.domain.value_objects.repo_url import RepoURL
from src.domain.value_objects.session_id import SessionId
from src.domain.exceptions.domain_exceptions import (
    CodebaseNotFoundError,
    CodebaseNotIndexedError,
    SessionNotFoundError,
)


@pytest.mark.asyncio
class TestIngestCodebaseUseCase:
    """Tests for IngestCodebaseUseCase."""

    @pytest.fixture
    def use_case(
        self,
        mock_codebase_repository,
        mock_git_service,
        mock_vector_store,
    ) -> IngestCodebaseUseCase:
        return IngestCodebaseUseCase(
            codebase_repository=mock_codebase_repository,
            git_service=mock_git_service,
            vector_store=mock_vector_store,
        )

    async def test_ingest_new_repository_success(
        self,
        use_case: IngestCodebaseUseCase,
        mock_codebase_repository,
        mock_git_service,
        mock_vector_store,
    ):
        """Test successful ingestion of a new repository."""
        request = IngestRequest(repo_url="https://github.com/owner/repo")

        result = await use_case.execute(request)

        assert result.status == IngestStatus.COMPLETED
        assert result.repo_url == "https://github.com/owner/repo"
        assert result.file_count == 2  # From mock_git_service.list_files
        assert result.error_message is None

        # Verify interactions
        mock_git_service.clone_repository.assert_called_once()
        mock_git_service.list_files.assert_called_once()
        mock_vector_store.create_index.assert_called_once()
        mock_vector_store.add_chunks.assert_called_once()
        assert mock_codebase_repository.save.call_count == 2  # Initial + completed

    async def test_ingest_already_indexed_repository(
        self,
        use_case: IngestCodebaseUseCase,
        mock_codebase_repository,
        mock_git_service,
    ):
        """Test ingestion returns existing codebase if already indexed."""
        existing = Codebase(
            id="existing-id",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/existing",
        )
        existing.mark_indexing_completed(50)
        mock_codebase_repository.get_by_url.return_value = existing

        request = IngestRequest(repo_url="https://github.com/owner/repo")
        result = await use_case.execute(request)

        assert result.codebase_id == "existing-id"
        assert result.status == IngestStatus.COMPLETED
        assert result.file_count == 50

        # Should not clone again
        mock_git_service.clone_repository.assert_not_called()

    async def test_ingest_clone_failure(
        self,
        use_case: IngestCodebaseUseCase,
        mock_codebase_repository,
        mock_git_service,
    ):
        """Test ingestion handles clone failure."""
        mock_git_service.clone_repository.side_effect = Exception("Clone failed: repo not found")

        request = IngestRequest(repo_url="https://github.com/owner/repo")
        result = await use_case.execute(request)

        assert result.status == IngestStatus.FAILED
        assert "Clone failed" in result.error_message

    async def test_ingest_indexing_failure(
        self,
        use_case: IngestCodebaseUseCase,
        mock_codebase_repository,
        mock_git_service,
        mock_vector_store,
    ):
        """Test ingestion handles indexing failure."""
        mock_vector_store.add_chunks.side_effect = Exception("Embedding API error")

        request = IngestRequest(repo_url="https://github.com/owner/repo")
        result = await use_case.execute(request)

        assert result.status == IngestStatus.FAILED
        assert "Embedding API error" in result.error_message

    async def test_ingest_empty_repository(
        self,
        use_case: IngestCodebaseUseCase,
        mock_codebase_repository,
        mock_git_service,
        mock_vector_store,
    ):
        """Test ingestion of repository with no matching files."""
        mock_git_service.list_files.return_value = []

        request = IngestRequest(repo_url="https://github.com/owner/repo")
        result = await use_case.execute(request)

        assert result.status == IngestStatus.COMPLETED
        assert result.file_count == 0


@pytest.mark.asyncio
class TestSendMessageUseCase:
    """Tests for SendMessageUseCase."""

    @pytest.fixture
    def use_case(
        self,
        mock_session_repository,
        mock_codebase_repository,
        mock_vector_store,
        mock_cache_service,
        mock_agent_runner,
    ) -> SendMessageUseCase:
        return SendMessageUseCase(
            session_repository=mock_session_repository,
            codebase_repository=mock_codebase_repository,
            vector_store=mock_vector_store,
            cache_service=mock_cache_service,
            agent_runner=mock_agent_runner,
        )

    @pytest.fixture
    def ready_codebase(self) -> Codebase:
        codebase = Codebase(
            id="ready-cb",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/ready-cb",
        )
        codebase.mark_indexing_completed(10)
        return codebase

    async def test_send_message_success(
        self,
        use_case: SendMessageUseCase,
        mock_codebase_repository,
        mock_session_repository,
        mock_agent_runner,
        ready_codebase,
    ):
        """Test successful message sending."""
        mock_codebase_repository.get_by_id.return_value = ready_codebase
        session_id = str(SessionId.generate())

        request = ChatRequest(message="What does main.py do?")
        result = await use_case.execute(
            session_id=session_id,
            codebase_id=ready_codebase.id,
            request=request,
        )

        assert result.session_id == session_id
        assert result.message.role == "assistant"
        assert "REST API" in result.message.content  # From mock
        assert result.sources == ["src/main.py", "src/api.py"]

        mock_agent_runner.run.assert_called_once()
        mock_session_repository.save.assert_called_once()

    async def test_send_message_codebase_not_found(
        self,
        use_case: SendMessageUseCase,
        mock_codebase_repository,
    ):
        """Test error when codebase not found."""
        mock_codebase_repository.get_by_id.return_value = None

        request = ChatRequest(message="Question")

        with pytest.raises(CodebaseNotFoundError):
            await use_case.execute(
                session_id=str(SessionId.generate()),
                codebase_id="nonexistent",
                request=request,
            )

    async def test_send_message_codebase_not_indexed(
        self,
        use_case: SendMessageUseCase,
        mock_codebase_repository,
    ):
        """Test error when codebase not indexed."""
        pending_codebase = Codebase(
            id="pending-cb",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/pending",
        )
        mock_codebase_repository.get_by_id.return_value = pending_codebase

        request = ChatRequest(message="Question")

        with pytest.raises(CodebaseNotIndexedError):
            await use_case.execute(
                session_id=str(SessionId.generate()),
                codebase_id="pending-cb",
                request=request,
            )

    async def test_send_message_cache_hit(
        self,
        use_case: SendMessageUseCase,
        mock_codebase_repository,
        mock_cache_service,
        mock_agent_runner,
        ready_codebase,
    ):
        """Test response is returned from cache."""
        mock_codebase_repository.get_by_id.return_value = ready_codebase
        mock_cache_service.get.return_value = {
            "response": "Cached response",
            "sources": ["cached.py"],
        }

        request = ChatRequest(message="Question", stream=False)
        result = await use_case.execute(
            session_id=str(SessionId.generate()),
            codebase_id=ready_codebase.id,
            request=request,
        )

        assert result.message.content == "Cached response"
        assert result.sources == ["cached.py"]
        mock_agent_runner.run.assert_not_called()

    async def test_send_message_cache_bypass_for_stream(
        self,
        use_case: SendMessageUseCase,
        mock_codebase_repository,
        mock_cache_service,
        mock_agent_runner,
        ready_codebase,
    ):
        """Test cache is bypassed for streaming requests."""
        mock_codebase_repository.get_by_id.return_value = ready_codebase
        mock_cache_service.get.return_value = {
            "response": "Cached",
            "sources": [],
        }

        request = ChatRequest(message="Question", stream=True)
        result = await use_case.execute(
            session_id=str(SessionId.generate()),
            codebase_id=ready_codebase.id,
            request=request,
        )

        # Agent should be called even with cache hit because stream=True
        mock_agent_runner.run.assert_called_once()

    async def test_send_message_creates_new_session(
        self,
        use_case: SendMessageUseCase,
        mock_codebase_repository,
        mock_session_repository,
        ready_codebase,
    ):
        """Test new session is created if not found."""
        mock_codebase_repository.get_by_id.return_value = ready_codebase
        mock_session_repository.get_by_id.return_value = None

        request = ChatRequest(message="First question")
        session_id = str(SessionId.generate())

        result = await use_case.execute(
            session_id=session_id,
            codebase_id=ready_codebase.id,
            request=request,
        )

        assert result.session_id == session_id
        mock_session_repository.save.assert_called_once()

    async def test_send_message_uses_existing_session(
        self,
        use_case: SendMessageUseCase,
        mock_codebase_repository,
        mock_session_repository,
        ready_codebase,
    ):
        """Test existing session is used if found."""
        mock_codebase_repository.get_by_id.return_value = ready_codebase
        session_id = SessionId.generate()
        existing_session = ChatSession(id=session_id, codebase_id=ready_codebase.id)
        existing_session.add_message(Message.user_message("Previous question"))
        mock_session_repository.get_by_id.return_value = existing_session

        request = ChatRequest(message="Follow-up question")
        result = await use_case.execute(
            session_id=str(session_id),
            codebase_id=ready_codebase.id,
            request=request,
        )

        assert result.session_id == str(session_id)


@pytest.mark.asyncio
class TestGetSessionUseCase:
    """Tests for GetSessionUseCase."""

    @pytest.fixture
    def use_case(self, mock_session_repository) -> GetSessionUseCase:
        return GetSessionUseCase(session_repository=mock_session_repository)

    async def test_get_session_success(
        self,
        use_case: GetSessionUseCase,
        mock_session_repository,
    ):
        """Test successful session retrieval."""
        session_id = SessionId.generate()
        session = ChatSession(id=session_id, codebase_id="cb-123")
        session.add_message(Message.user_message("Hello"))
        session.add_message(Message.assistant_message("Hi there!"))
        mock_session_repository.get_by_id.return_value = session

        result = await use_case.execute(str(session_id))

        assert result.id == str(session_id)
        assert result.codebase_id == "cb-123"
        assert result.message_count == 2
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "assistant"

    async def test_get_session_not_found(
        self,
        use_case: GetSessionUseCase,
        mock_session_repository,
    ):
        """Test error when session not found."""
        mock_session_repository.get_by_id.return_value = None

        with pytest.raises(SessionNotFoundError):
            await use_case.execute(str(SessionId.generate()))

    async def test_get_session_without_messages(
        self,
        use_case: GetSessionUseCase,
        mock_session_repository,
    ):
        """Test session retrieval without messages."""
        session_id = SessionId.generate()
        session = ChatSession(id=session_id, codebase_id="cb-123")
        session.add_message(Message.user_message("Hello"))
        mock_session_repository.get_by_id.return_value = session

        result = await use_case.execute(str(session_id), include_messages=False)

        assert result.id == str(session_id)
        assert result.message_count == 1
        assert result.messages is None

    async def test_get_session_includes_title(
        self,
        use_case: GetSessionUseCase,
        mock_session_repository,
    ):
        """Test session title is included."""
        session_id = SessionId.generate()
        session = ChatSession(id=session_id, codebase_id="cb-123")
        session.add_message(Message.user_message("What is the main function?"))
        mock_session_repository.get_by_id.return_value = session

        result = await use_case.execute(str(session_id))

        assert result.title == "What is the main function?"

    async def test_get_session_invalid_id_format(
        self,
        use_case: GetSessionUseCase,
    ):
        """Test error with invalid session ID format."""
        from src.domain.exceptions.domain_exceptions import InvalidSessionIdError

        with pytest.raises(InvalidSessionIdError):
            await use_case.execute("not-a-uuid")
