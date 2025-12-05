"""
Shared pytest fixtures for all tests.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from typing import List

from src.domain.value_objects.repo_url import RepoURL
from src.domain.value_objects.session_id import SessionId
from src.domain.value_objects.file_path import FilePath
from src.domain.entities.codebase import Codebase, IndexingStatus
from src.domain.entities.chat_session import ChatSession
from src.domain.entities.message import Message, MessageRole
from src.domain.repositories.i_codebase_repository import ICodebaseRepository
from src.domain.repositories.i_chat_session_repository import IChatSessionRepository
from src.application.interfaces.i_git_service import IGitService
from src.application.interfaces.i_vector_store import IVectorStore, CodeChunk, SearchResult
from src.application.interfaces.i_cache_service import ICacheService


# ============================================================================
# Value Object Fixtures
# ============================================================================


@pytest.fixture
def valid_github_url() -> str:
    return "https://github.com/owner/repo"


@pytest.fixture
def valid_github_url_with_git() -> str:
    return "https://github.com/owner/repo.git"


@pytest.fixture
def test_repo_url(valid_github_url: str) -> RepoURL:
    return RepoURL(valid_github_url)


@pytest.fixture
def test_session_id() -> SessionId:
    return SessionId.generate()


@pytest.fixture
def test_file_path() -> FilePath:
    return FilePath("src/main.py")


# ============================================================================
# Entity Fixtures
# ============================================================================


@pytest.fixture
def test_codebase(test_repo_url: RepoURL) -> Codebase:
    return Codebase(
        id="test-codebase-id",
        repo_url=test_repo_url,
        local_path="./repos/test-codebase-id",
    )


@pytest.fixture
def completed_codebase(test_repo_url: RepoURL) -> Codebase:
    codebase = Codebase(
        id="completed-codebase-id",
        repo_url=test_repo_url,
        local_path="./repos/completed-codebase-id",
    )
    codebase.mark_indexing_completed(42)
    return codebase


@pytest.fixture
def test_session(test_session_id: SessionId) -> ChatSession:
    return ChatSession(
        id=test_session_id,
        codebase_id="test-codebase-id",
    )


@pytest.fixture
def test_user_message() -> Message:
    return Message.user_message("What does this code do?")


@pytest.fixture
def test_assistant_message() -> Message:
    return Message.assistant_message(
        "This code implements a REST API.",
        metadata={"sources": ["src/main.py"]},
    )


# ============================================================================
# Mock Repository Fixtures
# ============================================================================


@pytest.fixture
def mock_codebase_repository() -> AsyncMock:
    """Mock ICodebaseRepository."""
    mock = AsyncMock(spec=ICodebaseRepository)
    mock.get_by_id.return_value = None
    mock.get_by_url.return_value = None
    mock.save.return_value = None
    mock.delete.return_value = None
    mock.list_all.return_value = []
    return mock


@pytest.fixture
def mock_session_repository() -> AsyncMock:
    """Mock IChatSessionRepository."""
    mock = AsyncMock(spec=IChatSessionRepository)
    mock.get_by_id.return_value = None
    mock.save.return_value = None
    mock.delete.return_value = None
    mock.list_by_codebase.return_value = []
    return mock


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_git_service() -> AsyncMock:
    """Mock IGitService."""
    mock = AsyncMock(spec=IGitService)
    mock.clone_repository.return_value = "./repos/test"
    mock.list_files.return_value = ["src/main.py", "src/utils.py"]
    mock.read_file.return_value = "# Sample code\ndef main():\n    pass"
    return mock


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    """Mock IVectorStore."""
    mock = AsyncMock(spec=IVectorStore)
    mock.create_index.return_value = None
    mock.add_chunks.return_value = None
    mock.delete_index.return_value = None
    mock.search.return_value = [
        SearchResult(
            chunk=CodeChunk(
                content="def main():\n    pass",
                file_path="src/main.py",
                start_line=1,
                end_line=2,
            ),
            score=0.95,
        )
    ]
    return mock


@pytest.fixture
def mock_cache_service() -> AsyncMock:
    """Mock ICacheService."""
    mock = AsyncMock(spec=ICacheService)
    mock.get.return_value = None
    mock.set.return_value = None
    mock.delete.return_value = None
    mock.exists.return_value = False
    mock.clear_pattern.return_value = None
    return mock


@pytest.fixture
def mock_agent_runner() -> AsyncMock:
    """Mock IAgentRunner for use cases."""
    mock = AsyncMock()
    mock.run.return_value = (
        "This code implements a REST API with FastAPI.",
        ["src/main.py", "src/api.py"],
    )
    return mock


# ============================================================================
# Code Chunk Fixtures
# ============================================================================


@pytest.fixture
def sample_code_chunks() -> List[CodeChunk]:
    return [
        CodeChunk(
            content="def main():\n    print('Hello')",
            file_path="src/main.py",
            start_line=1,
            end_line=2,
        ),
        CodeChunk(
            content="def helper():\n    return 42",
            file_path="src/utils.py",
            start_line=1,
            end_line=2,
        ),
    ]


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
