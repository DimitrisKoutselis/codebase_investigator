"""
Integration tests for infrastructure components.

These tests verify that infrastructure implementations work correctly.
For Redis tests, we mock the Redis client to avoid requiring a live server.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from pathlib import Path

from src.infrastructure.repositories.redis_codebase_repository import (
    RedisCodebaseRepository,
)
from src.infrastructure.repositories.redis_session_repository import (
    RedisSessionRepository,
)
from src.infrastructure.cache.redis_cache import RedisCacheService
from src.infrastructure.git.git_service import GitService
from src.domain.entities.codebase import Codebase, IndexingStatus
from src.domain.entities.chat_session import ChatSession
from src.domain.entities.message import Message, MessageRole
from src.domain.value_objects.repo_url import RepoURL
from src.domain.value_objects.session_id import SessionId


@pytest.mark.asyncio
class TestRedisCodebaseRepository:
    """Tests for RedisCodebaseRepository."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        client = AsyncMock()
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock()
        client.delete = AsyncMock()
        client.sadd = AsyncMock()
        client.srem = AsyncMock()
        client.smembers = AsyncMock(return_value=set())
        return client

    @pytest.fixture
    def repository(self, mock_redis_client):
        """Create repository with mock client."""
        repo = RedisCodebaseRepository(redis_url="redis://localhost:6379")
        repo._client = mock_redis_client
        return repo

    @pytest.fixture
    def sample_codebase(self) -> Codebase:
        return Codebase(
            id="cb-123",
            repo_url=RepoURL("https://github.com/owner/repo"),
            local_path="./repos/cb-123",
        )

    async def test_save_codebase(self, repository, mock_redis_client, sample_codebase):
        """Test saving a codebase."""
        await repository.save(sample_codebase)

        # Verify set was called for main record (first call)
        calls = mock_redis_client.set.call_args_list
        assert len(calls) >= 2

        # Verify first call is for codebase data
        first_call = calls[0]
        assert first_call[0][0] == "codebase:cb-123"
        assert isinstance(first_call[0][1], str)  # JSON string

        # Verify URL index created
        mock_redis_client.set.assert_any_call(
            f"codebase:url:{sample_codebase.repo_url}",
            "cb-123",
        )

        # Verify added to all codebases set
        mock_redis_client.sadd.assert_called_once_with("codebases:all", "cb-123")

    async def test_get_by_id_found(self, repository, mock_redis_client, sample_codebase):
        """Test retrieving codebase by ID."""
        serialized = repository._serialize_codebase(sample_codebase)
        mock_redis_client.get.return_value = serialized

        result = await repository.get_by_id("cb-123")

        assert result is not None
        assert result.id == "cb-123"
        assert str(result.repo_url) == "https://github.com/owner/repo"

    async def test_get_by_id_not_found(self, repository, mock_redis_client):
        """Test retrieving non-existent codebase."""
        mock_redis_client.get.return_value = None

        result = await repository.get_by_id("nonexistent")

        assert result is None

    async def test_get_by_url_found(self, repository, mock_redis_client, sample_codebase):
        """Test retrieving codebase by URL."""
        serialized = repository._serialize_codebase(sample_codebase)
        mock_redis_client.get.side_effect = ["cb-123", serialized]

        result = await repository.get_by_url(sample_codebase.repo_url)

        assert result is not None
        assert result.id == "cb-123"

    async def test_get_by_url_not_found(self, repository, mock_redis_client):
        """Test retrieving non-existent URL."""
        mock_redis_client.get.return_value = None

        result = await repository.get_by_url(RepoURL("https://github.com/other/repo"))

        assert result is None

    async def test_delete_codebase(self, repository, mock_redis_client, sample_codebase):
        """Test deleting a codebase."""
        serialized = repository._serialize_codebase(sample_codebase)
        mock_redis_client.get.return_value = serialized

        await repository.delete("cb-123")

        mock_redis_client.delete.assert_any_call(
            f"codebase:url:{sample_codebase.repo_url}"
        )
        mock_redis_client.delete.assert_any_call("codebase:cb-123")
        mock_redis_client.srem.assert_called_once_with("codebases:all", "cb-123")

    async def test_list_all_codebases(self, repository, mock_redis_client, sample_codebase):
        """Test listing all codebases."""
        mock_redis_client.smembers.return_value = {"cb-123", "cb-456"}
        serialized1 = repository._serialize_codebase(sample_codebase)

        codebase2 = Codebase(
            id="cb-456",
            repo_url=RepoURL("https://github.com/other/repo"),
            local_path="./repos/cb-456",
        )
        serialized2 = repository._serialize_codebase(codebase2)

        mock_redis_client.get.side_effect = [serialized1, serialized2]

        result = await repository.list_all()

        assert len(result) == 2

    async def test_serialization_round_trip(self, repository, sample_codebase):
        """Test serialization and deserialization preserves data."""
        sample_codebase.mark_indexing_completed(50)

        serialized = repository._serialize_codebase(sample_codebase)
        deserialized = repository._deserialize_codebase(serialized)

        assert deserialized.id == sample_codebase.id
        assert str(deserialized.repo_url) == str(sample_codebase.repo_url)
        assert deserialized.indexing_status == IndexingStatus.COMPLETED
        assert deserialized.file_count == 50


@pytest.mark.asyncio
class TestRedisSessionRepository:
    """Tests for RedisSessionRepository."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        client = AsyncMock()
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock()
        client.delete = AsyncMock()
        client.sadd = AsyncMock()
        client.srem = AsyncMock()
        client.smembers = AsyncMock(return_value=set())
        return client

    @pytest.fixture
    def repository(self, mock_redis_client):
        """Create repository with mock client."""
        repo = RedisSessionRepository(redis_url="redis://localhost:6379")
        repo._client = mock_redis_client
        return repo

    @pytest.fixture
    def sample_session(self) -> ChatSession:
        session = ChatSession(
            id=SessionId.generate(),
            codebase_id="cb-123",
        )
        session.add_message(Message.user_message("Hello"))
        session.add_message(Message.assistant_message("Hi there!"))
        return session

    async def test_save_session(self, repository, mock_redis_client, sample_session):
        """Test saving a session."""
        await repository.save(sample_session)

        mock_redis_client.set.assert_called_once()
        mock_redis_client.sadd.assert_called_once_with(
            f"codebase:{sample_session.codebase_id}:sessions",
            str(sample_session.id),
        )

    async def test_get_by_id_found(self, repository, mock_redis_client, sample_session):
        """Test retrieving session by ID."""
        serialized = repository._serialize_session(sample_session)
        mock_redis_client.get.return_value = serialized

        result = await repository.get_by_id(sample_session.id)

        assert result is not None
        assert str(result.id) == str(sample_session.id)
        assert len(result.messages) == 2

    async def test_get_by_id_not_found(self, repository, mock_redis_client):
        """Test retrieving non-existent session."""
        mock_redis_client.get.return_value = None

        result = await repository.get_by_id(SessionId.generate())

        assert result is None

    async def test_delete_session(self, repository, mock_redis_client, sample_session):
        """Test deleting a session."""
        serialized = repository._serialize_session(sample_session)
        mock_redis_client.get.return_value = serialized

        await repository.delete(sample_session.id)

        mock_redis_client.srem.assert_called_once()
        mock_redis_client.delete.assert_called_once()

    async def test_list_by_codebase(self, repository, mock_redis_client, sample_session):
        """Test listing sessions by codebase."""
        mock_redis_client.smembers.return_value = {str(sample_session.id)}
        serialized = repository._serialize_session(sample_session)
        mock_redis_client.get.return_value = serialized

        result = await repository.list_by_codebase("cb-123")

        assert len(result) == 1
        assert str(result[0].id) == str(sample_session.id)

    async def test_serialization_preserves_messages(self, repository, sample_session):
        """Test serialization preserves all message data."""
        serialized = repository._serialize_session(sample_session)
        deserialized = repository._deserialize_session(serialized)

        assert len(deserialized.messages) == 2
        assert deserialized.messages[0].role == MessageRole.USER
        assert deserialized.messages[0].content == "Hello"
        assert deserialized.messages[1].role == MessageRole.ASSISTANT
        assert deserialized.messages[1].content == "Hi there!"


@pytest.mark.asyncio
class TestRedisCacheService:
    """Tests for RedisCacheService."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        client = AsyncMock()
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock()
        client.delete = AsyncMock()
        client.exists = AsyncMock(return_value=0)
        client.scan = AsyncMock(return_value=(0, []))
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def cache_service(self, mock_redis_client):
        """Create cache service with mock client."""
        service = RedisCacheService(redis_url="redis://localhost:6379", default_ttl=3600)
        service._client = mock_redis_client
        return service

    async def test_get_string_value(self, cache_service, mock_redis_client):
        """Test getting a string value."""
        mock_redis_client.get.return_value = "simple string"

        result = await cache_service.get("key")

        assert result == "simple string"

    async def test_get_json_value(self, cache_service, mock_redis_client):
        """Test getting a JSON value."""
        mock_redis_client.get.return_value = '{"name": "test", "value": 42}'

        result = await cache_service.get("key")

        assert result == {"name": "test", "value": 42}

    async def test_get_none_for_missing_key(self, cache_service, mock_redis_client):
        """Test getting a missing key returns None."""
        mock_redis_client.get.return_value = None

        result = await cache_service.get("missing")

        assert result is None

    async def test_set_string_value(self, cache_service, mock_redis_client):
        """Test setting a string value."""
        await cache_service.set("key", "value", ttl_seconds=60)

        mock_redis_client.set.assert_called_once_with("key", "value", ex=60)

    async def test_set_dict_value_serializes_to_json(self, cache_service, mock_redis_client):
        """Test setting a dict value serializes to JSON."""
        await cache_service.set("key", {"name": "test"})

        mock_redis_client.set.assert_called_once()
        call_args = mock_redis_client.set.call_args
        assert json.loads(call_args[0][1]) == {"name": "test"}

    async def test_set_uses_default_ttl(self, cache_service, mock_redis_client):
        """Test setting uses default TTL when not specified."""
        await cache_service.set("key", "value")

        mock_redis_client.set.assert_called_once_with("key", "value", ex=3600)

    async def test_delete_key(self, cache_service, mock_redis_client):
        """Test deleting a key."""
        await cache_service.delete("key")

        mock_redis_client.delete.assert_called_once_with("key")

    async def test_exists_true(self, cache_service, mock_redis_client):
        """Test exists returns True for existing key."""
        mock_redis_client.exists.return_value = 1

        result = await cache_service.exists("key")

        assert result is True

    async def test_exists_false(self, cache_service, mock_redis_client):
        """Test exists returns False for missing key."""
        mock_redis_client.exists.return_value = 0

        result = await cache_service.exists("missing")

        assert result is False

    async def test_clear_pattern(self, cache_service, mock_redis_client):
        """Test clearing keys by pattern."""
        mock_redis_client.scan.side_effect = [
            (1, ["key1", "key2"]),
            (0, ["key3"]),
        ]

        await cache_service.clear_pattern("prefix:*")

        assert mock_redis_client.delete.call_count == 2

    async def test_close(self, cache_service, mock_redis_client):
        """Test closing the connection."""
        await cache_service.close()

        mock_redis_client.close.assert_called_once()
        assert cache_service._client is None


@pytest.mark.asyncio
class TestGitService:
    """Tests for GitService."""

    @pytest.fixture
    def git_service(self):
        return GitService()

    async def test_list_files_filters_by_extension(self, git_service, tmp_path):
        """Test that list_files filters by extension."""
        # Create test files
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "utils.py").write_text("def helper(): pass")
        (tmp_path / "readme.txt").write_text("readme")
        (tmp_path / "config.json").write_text("{}")

        files = await git_service.list_files(str(tmp_path), extensions=[".py"])

        assert len(files) == 2
        assert "main.py" in files
        assert "utils.py" in files
        assert "readme.txt" not in files

    async def test_list_files_uses_default_extensions(self, git_service, tmp_path):
        """Test that list_files uses default extensions when none specified."""
        (tmp_path / "main.py").write_text("code")
        (tmp_path / "app.js").write_text("code")
        (tmp_path / "image.png").write_bytes(b"binary")

        files = await git_service.list_files(str(tmp_path))

        assert "main.py" in files
        assert "app.js" in files
        assert "image.png" not in files

    async def test_list_files_ignores_directories(self, git_service, tmp_path):
        """Test that list_files ignores certain directories."""
        # Create files in ignored directories
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.js").write_text("code")

        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cache.py").write_text("code")

        # Create regular file
        (tmp_path / "main.py").write_text("code")

        files = await git_service.list_files(str(tmp_path), extensions=[".py", ".js"])

        assert "main.py" in files
        assert len([f for f in files if "node_modules" in f]) == 0
        assert len([f for f in files if "__pycache__" in f]) == 0

    async def test_list_files_returns_relative_paths(self, git_service, tmp_path):
        """Test that list_files returns relative paths."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("code")

        files = await git_service.list_files(str(tmp_path), extensions=[".py"])

        assert "src/main.py" in files or "src\\main.py" in files

    async def test_read_file(self, git_service, tmp_path):
        """Test reading a file."""
        content = "def main():\n    print('hello')"
        (tmp_path / "main.py").write_text(content)

        result = await git_service.read_file(str(tmp_path), "main.py")

        assert result == content

    async def test_read_file_handles_encoding(self, git_service, tmp_path):
        """Test reading a file with special characters."""
        content = "# -*- coding: utf-8 -*-\n# Comment: héllo wörld"
        (tmp_path / "main.py").write_text(content, encoding="utf-8")

        result = await git_service.read_file(str(tmp_path), "main.py")

        assert "héllo wörld" in result

    async def test_clone_repository(self, git_service, tmp_path):
        """Test cloning a repository (mocked)."""
        with patch("src.infrastructure.git.git_service.Repo") as mock_repo:
            mock_repo.clone_from.return_value = MagicMock()

            repo_url = RepoURL("https://github.com/owner/repo")
            target = str(tmp_path / "cloned")

            result = await git_service.clone_repository(repo_url, target)

            assert result == target
            mock_repo.clone_from.assert_called_once_with(
                repo_url.clone_url, target, depth=1
            )

    def test_supported_extensions(self, git_service):
        """Test supported extensions include common languages."""
        assert ".py" in git_service.SUPPORTED_EXTENSIONS
        assert ".js" in git_service.SUPPORTED_EXTENSIONS
        assert ".ts" in git_service.SUPPORTED_EXTENSIONS
        assert ".md" in git_service.SUPPORTED_EXTENSIONS
        assert ".json" in git_service.SUPPORTED_EXTENSIONS

    def test_ignored_directories(self, git_service):
        """Test ignored directories include common ones."""
        assert ".git" in git_service.IGNORED_DIRS
        assert "node_modules" in git_service.IGNORED_DIRS
        assert "__pycache__" in git_service.IGNORED_DIRS
        assert ".venv" in git_service.IGNORED_DIRS
