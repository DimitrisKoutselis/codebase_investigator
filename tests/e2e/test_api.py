"""
End-to-end tests for API endpoints.

These tests verify the full API behavior using FastAPI's TestClient
with properly overridden dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient

from src.presentation.main import create_app
from src.presentation.api.dependencies import (
    get_codebase_repository,
    get_session_repository,
    get_git_service,
    get_vector_store,
    get_cache_service,
    get_rag_graph,
    get_ingest_use_case,
    get_send_message_use_case,
    get_session_use_case,
)
from src.domain.entities.codebase import Codebase, IndexingStatus
from src.domain.entities.chat_session import ChatSession
from src.domain.entities.message import Message
from src.domain.value_objects.repo_url import RepoURL
from src.domain.value_objects.session_id import SessionId
from src.application.use_cases.ingest_codebase import IngestCodebaseUseCase
from src.application.use_cases.send_message import SendMessageUseCase
from src.application.use_cases.get_session import GetSessionUseCase


class TestHealthEndpoints:
    """Tests for health and root endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Codebase Investigator"
        assert data["version"] == "1.0.0"
        assert "docs" in data
        assert "health" in data


class TestIngestEndpoints:
    """Tests for ingestion endpoints."""

    @pytest.fixture
    def mock_codebase_repo(self):
        """Create mock codebase repository."""
        mock = AsyncMock()
        mock.get_by_url.return_value = None
        mock.get_by_id.return_value = None
        mock.save.return_value = None
        mock.list_all.return_value = []
        return mock

    @pytest.fixture
    def mock_git_service(self):
        """Create mock git service."""
        mock = AsyncMock()
        mock.clone_repository.return_value = "./repos/test"
        mock.list_files.return_value = ["main.py"]
        mock.read_file.return_value = "print('hello')"
        return mock

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        mock = AsyncMock()
        mock.create_index.return_value = None
        mock.add_chunks.return_value = None
        return mock

    @pytest.fixture
    def client(self, mock_codebase_repo, mock_git_service, mock_vector_store):
        """Create test client with mocked dependencies."""
        app = create_app()

        # Create mock use case
        mock_ingest_use_case = IngestCodebaseUseCase(
            codebase_repository=mock_codebase_repo,
            git_service=mock_git_service,
            vector_store=mock_vector_store,
        )

        # Override dependencies
        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo
        app.dependency_overrides[get_git_service] = lambda: mock_git_service
        app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
        app.dependency_overrides[get_ingest_use_case] = lambda: mock_ingest_use_case

        return TestClient(app)

    def test_ingest_valid_repository(self, client):
        """Test ingesting a valid repository."""
        response = client.post(
            "/ingest",
            json={"repo_url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "codebase_id" in data
        assert data["status"] == "completed"

    def test_ingest_invalid_url(self, client):
        """Test ingesting with invalid URL."""
        response = client.post(
            "/ingest",
            json={"repo_url": "not-a-valid-url"},
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_ingest_already_indexed(self, mock_codebase_repo, mock_git_service, mock_vector_store):
        """Test ingesting an already indexed repository."""
        app = create_app()

        existing = Codebase(
            id="existing-id",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/existing",
        )
        existing.mark_indexing_completed(10)
        mock_codebase_repo.get_by_url.return_value = existing

        mock_ingest_use_case = IngestCodebaseUseCase(
            codebase_repository=mock_codebase_repo,
            git_service=mock_git_service,
            vector_store=mock_vector_store,
        )

        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo
        app.dependency_overrides[get_ingest_use_case] = lambda: mock_ingest_use_case

        client = TestClient(app)
        response = client.post(
            "/ingest",
            json={"repo_url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["codebase_id"] == "existing-id"
        assert data["status"] == "completed"

    def test_get_ingestion_status(self, mock_codebase_repo):
        """Test getting ingestion status."""
        app = create_app()

        codebase = Codebase(
            id="cb-123",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/cb-123",
        )
        codebase.mark_indexing_completed(42)
        mock_codebase_repo.get_by_id.return_value = codebase

        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo

        client = TestClient(app)
        response = client.get("/ingest/cb-123")

        assert response.status_code == 200
        data = response.json()
        assert data["codebase_id"] == "cb-123"
        assert data["status"] == "completed"
        assert data["file_count"] == 42

    def test_get_ingestion_status_not_found(self, mock_codebase_repo):
        """Test getting status for non-existent codebase."""
        app = create_app()
        mock_codebase_repo.get_by_id.return_value = None

        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo

        client = TestClient(app)
        response = client.get("/ingest/nonexistent")

        assert response.status_code == 404

    def test_list_codebases(self, mock_codebase_repo):
        """Test listing all codebases."""
        app = create_app()

        codebase1 = Codebase(
            id="cb-1",
            repo_url=RepoURL("https://github.com/owner/repo1"),
            local_path="./repos/cb-1",
        )
        codebase2 = Codebase(
            id="cb-2",
            repo_url=RepoURL("https://github.com/owner/repo2"),
            local_path="./repos/cb-2",
        )
        mock_codebase_repo.list_all.return_value = [codebase1, codebase2]

        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo

        client = TestClient(app)
        response = client.get("/ingest")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_codebases_empty(self, mock_codebase_repo):
        """Test listing codebases when empty."""
        app = create_app()
        mock_codebase_repo.list_all.return_value = []

        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo

        client = TestClient(app)
        response = client.get("/ingest")

        assert response.status_code == 200
        assert response.json() == []


class TestChatEndpoints:
    """Tests for chat endpoints."""

    @pytest.fixture
    def mock_codebase_repo(self):
        """Create mock codebase repository with ready codebase."""
        mock = AsyncMock()
        ready_codebase = Codebase(
            id="ready-cb",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/ready",
        )
        ready_codebase.mark_indexing_completed(10)
        mock.get_by_id.return_value = ready_codebase
        return mock

    @pytest.fixture
    def mock_session_repo(self):
        """Create mock session repository."""
        mock = AsyncMock()
        mock.get_by_id.return_value = None
        mock.save.return_value = None
        return mock

    @pytest.fixture
    def mock_cache_service(self):
        """Create mock cache service."""
        mock = AsyncMock()
        mock.get.return_value = None
        mock.set.return_value = None
        return mock

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        return AsyncMock()

    @pytest.fixture
    def mock_rag_graph(self):
        """Create mock RAG graph."""
        mock = AsyncMock()
        mock.run.return_value = ("This is the answer.", ["file.py"])
        return mock

    def test_send_message_success(
        self,
        mock_codebase_repo,
        mock_session_repo,
        mock_cache_service,
        mock_vector_store,
        mock_rag_graph,
    ):
        """Test sending a message successfully."""
        app = create_app()

        mock_use_case = SendMessageUseCase(
            session_repository=mock_session_repo,
            codebase_repository=mock_codebase_repo,
            vector_store=mock_vector_store,
            cache_service=mock_cache_service,
            agent_runner=mock_rag_graph,
        )

        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo
        app.dependency_overrides[get_session_repository] = lambda: mock_session_repo
        app.dependency_overrides[get_cache_service] = lambda: mock_cache_service
        app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
        app.dependency_overrides[get_rag_graph] = lambda: mock_rag_graph
        app.dependency_overrides[get_send_message_use_case] = lambda: mock_use_case

        client = TestClient(app)
        session_id = str(SessionId.generate())

        response = client.post(
            f"/chat/ready-cb/{session_id}",
            json={"message": "What does this code do?", "stream": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["message"]["role"] == "assistant"

    def test_send_message_codebase_not_found(
        self,
        mock_session_repo,
        mock_cache_service,
        mock_vector_store,
        mock_rag_graph,
    ):
        """Test sending message to non-existent codebase."""
        app = create_app()

        mock_codebase_repo = AsyncMock()
        mock_codebase_repo.get_by_id.return_value = None

        mock_use_case = SendMessageUseCase(
            session_repository=mock_session_repo,
            codebase_repository=mock_codebase_repo,
            vector_store=mock_vector_store,
            cache_service=mock_cache_service,
            agent_runner=mock_rag_graph,
        )

        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo
        app.dependency_overrides[get_send_message_use_case] = lambda: mock_use_case

        client = TestClient(app)
        response = client.post(
            f"/chat/nonexistent/{SessionId.generate()}",
            json={"message": "Hello"},
        )

        assert response.status_code == 404

    def test_send_message_codebase_not_indexed(
        self,
        mock_session_repo,
        mock_cache_service,
        mock_vector_store,
        mock_rag_graph,
    ):
        """Test sending message to non-indexed codebase."""
        app = create_app()

        mock_codebase_repo = AsyncMock()
        pending = Codebase(
            id="pending-cb",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/pending",
        )
        mock_codebase_repo.get_by_id.return_value = pending

        mock_use_case = SendMessageUseCase(
            session_repository=mock_session_repo,
            codebase_repository=mock_codebase_repo,
            vector_store=mock_vector_store,
            cache_service=mock_cache_service,
            agent_runner=mock_rag_graph,
        )

        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo
        app.dependency_overrides[get_send_message_use_case] = lambda: mock_use_case

        client = TestClient(app)
        response = client.post(
            f"/chat/pending-cb/{SessionId.generate()}",
            json={"message": "Hello"},
        )

        assert response.status_code == 400


class TestSessionEndpoints:
    """Tests for session endpoints."""

    @pytest.fixture
    def mock_session_repo(self):
        """Create mock session repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_codebase_repo(self):
        """Create mock codebase repository."""
        return AsyncMock()

    def test_get_session_success(self, mock_session_repo):
        """Test getting a session successfully."""
        app = create_app()

        session_id = SessionId.generate()
        session = ChatSession(id=session_id, codebase_id="cb-123")
        session.add_message(Message.user_message("Hello"))
        session.add_message(Message.assistant_message("Hi there!"))
        mock_session_repo.get_by_id.return_value = session

        mock_use_case = GetSessionUseCase(session_repository=mock_session_repo)

        app.dependency_overrides[get_session_repository] = lambda: mock_session_repo
        app.dependency_overrides[get_session_use_case] = lambda: mock_use_case

        client = TestClient(app)
        response = client.get(f"/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(session_id)
        assert data["message_count"] == 2
        assert len(data["messages"]) == 2

    def test_get_session_not_found(self, mock_session_repo):
        """Test getting non-existent session."""
        app = create_app()

        mock_session_repo.get_by_id.return_value = None
        mock_use_case = GetSessionUseCase(session_repository=mock_session_repo)

        app.dependency_overrides[get_session_repository] = lambda: mock_session_repo
        app.dependency_overrides[get_session_use_case] = lambda: mock_use_case

        client = TestClient(app)
        response = client.get(f"/sessions/{SessionId.generate()}")

        assert response.status_code == 404

    def test_get_session_without_messages(self, mock_session_repo):
        """Test getting session without messages."""
        app = create_app()

        session_id = SessionId.generate()
        session = ChatSession(id=session_id, codebase_id="cb-123")
        session.add_message(Message.user_message("Hello"))
        mock_session_repo.get_by_id.return_value = session

        mock_use_case = GetSessionUseCase(session_repository=mock_session_repo)

        app.dependency_overrides[get_session_repository] = lambda: mock_session_repo
        app.dependency_overrides[get_session_use_case] = lambda: mock_use_case

        client = TestClient(app)
        response = client.get(f"/sessions/{session_id}?include_messages=false")

        assert response.status_code == 200
        data = response.json()
        assert data["messages"] is None

    def test_list_sessions_by_codebase(self, mock_session_repo, mock_codebase_repo):
        """Test listing sessions by codebase."""
        app = create_app()

        codebase = Codebase(
            id="cb-123",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/cb-123",
        )
        mock_codebase_repo.get_by_id.return_value = codebase

        session1 = ChatSession(id=SessionId.generate(), codebase_id="cb-123")
        session2 = ChatSession(id=SessionId.generate(), codebase_id="cb-123")
        mock_session_repo.list_by_codebase.return_value = [session1, session2]

        app.dependency_overrides[get_session_repository] = lambda: mock_session_repo
        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo

        client = TestClient(app)
        response = client.get("/sessions/codebase/cb-123")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["sessions"]) == 2

    def test_list_sessions_codebase_not_found(self, mock_session_repo, mock_codebase_repo):
        """Test listing sessions for non-existent codebase."""
        app = create_app()

        mock_codebase_repo.get_by_id.return_value = None

        app.dependency_overrides[get_session_repository] = lambda: mock_session_repo
        app.dependency_overrides[get_codebase_repository] = lambda: mock_codebase_repo

        client = TestClient(app)
        response = client.get("/sessions/codebase/nonexistent")

        assert response.status_code == 404

    def test_delete_session(self, mock_session_repo):
        """Test deleting a session."""
        app = create_app()

        app.dependency_overrides[get_session_repository] = lambda: mock_session_repo

        client = TestClient(app)
        response = client.delete(f"/sessions/{SessionId.generate()}")

        assert response.status_code == 204


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestAPIDocumentation:
    """Tests for API documentation."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Codebase Investigator"
        assert "paths" in schema

    def test_swagger_docs_available(self, client):
        """Test that Swagger docs are available."""
        response = client.get("/docs")

        assert response.status_code == 200
