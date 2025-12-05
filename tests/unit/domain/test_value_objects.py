"""
Unit tests for domain value objects.
"""

import pytest
import uuid

from src.domain.value_objects.repo_url import RepoURL
from src.domain.value_objects.session_id import SessionId
from src.domain.value_objects.file_path import FilePath
from src.domain.exceptions.domain_exceptions import (
    InvalidRepositoryURLError,
    InvalidSessionIdError,
    InvalidFilePathError,
)


class TestRepoURL:
    """Tests for RepoURL value object."""

    def test_valid_github_url(self):
        """Test creation with a valid GitHub URL."""
        url = RepoURL("https://github.com/owner/repo")
        assert url.value == "https://github.com/owner/repo"

    def test_valid_github_url_with_git_extension(self):
        """Test creation with .git extension."""
        url = RepoURL("https://github.com/owner/repo.git")
        assert url.value == "https://github.com/owner/repo.git"

    def test_valid_github_url_with_trailing_slash(self):
        """Test creation with trailing slash."""
        url = RepoURL("https://github.com/owner/repo/")
        assert url.value == "https://github.com/owner/repo/"

    def test_valid_http_url(self):
        """Test creation with HTTP (not HTTPS)."""
        url = RepoURL("http://github.com/owner/repo")
        assert url.value == "http://github.com/owner/repo"

    def test_valid_url_with_dashes_and_dots(self):
        """Test creation with dashes and dots in owner/repo names."""
        url = RepoURL("https://github.com/my-org/my.repo.name")
        assert url.value == "https://github.com/my-org/my.repo.name"

    def test_invalid_non_github_url(self):
        """Test rejection of non-GitHub URLs."""
        with pytest.raises(InvalidRepositoryURLError):
            RepoURL("https://gitlab.com/owner/repo")

    def test_invalid_malformed_url(self):
        """Test rejection of malformed URLs."""
        with pytest.raises(InvalidRepositoryURLError):
            RepoURL("not-a-url")

    def test_invalid_missing_repo(self):
        """Test rejection of URL without repo name."""
        with pytest.raises(InvalidRepositoryURLError):
            RepoURL("https://github.com/owner")

    def test_invalid_missing_owner(self):
        """Test rejection of URL without owner."""
        with pytest.raises(InvalidRepositoryURLError):
            RepoURL("https://github.com/")

    def test_invalid_empty_string(self):
        """Test rejection of empty string."""
        with pytest.raises(InvalidRepositoryURLError):
            RepoURL("")

    def test_owner_property(self):
        """Test extraction of owner from URL."""
        url = RepoURL("https://github.com/anthropic/claude")
        assert url.owner == "anthropic"

    def test_owner_property_with_git_extension(self):
        """Test owner extraction from URL with .git extension."""
        url = RepoURL("https://github.com/anthropic/claude.git")
        assert url.owner == "anthropic"

    def test_repo_name_property(self):
        """Test extraction of repo name from URL."""
        url = RepoURL("https://github.com/anthropic/claude")
        assert url.repo_name == "claude"

    def test_repo_name_property_with_git_extension(self):
        """Test repo name extraction from URL with .git extension."""
        url = RepoURL("https://github.com/anthropic/claude.git")
        assert url.repo_name == "claude"

    def test_repo_name_property_with_trailing_slash(self):
        """Test repo name extraction from URL with trailing slash."""
        url = RepoURL("https://github.com/anthropic/claude/")
        assert url.repo_name == "claude"

    def test_clone_url_property_adds_git_extension(self):
        """Test clone_url adds .git extension if missing."""
        url = RepoURL("https://github.com/owner/repo")
        assert url.clone_url == "https://github.com/owner/repo.git"

    def test_clone_url_property_preserves_git_extension(self):
        """Test clone_url preserves .git extension if present."""
        url = RepoURL("https://github.com/owner/repo.git")
        assert url.clone_url == "https://github.com/owner/repo.git"

    def test_str_representation(self):
        """Test string representation."""
        url = RepoURL("https://github.com/owner/repo")
        assert str(url) == "https://github.com/owner/repo"

    def test_immutability(self):
        """Test that the value object is immutable."""
        url = RepoURL("https://github.com/owner/repo")
        with pytest.raises(AttributeError):
            url.value = "https://github.com/other/repo"

    def test_equality(self):
        """Test equality comparison."""
        url1 = RepoURL("https://github.com/owner/repo")
        url2 = RepoURL("https://github.com/owner/repo")
        assert url1 == url2

    def test_inequality(self):
        """Test inequality comparison."""
        url1 = RepoURL("https://github.com/owner/repo1")
        url2 = RepoURL("https://github.com/owner/repo2")
        assert url1 != url2


class TestSessionId:
    """Tests for SessionId value object."""

    def test_valid_uuid(self):
        """Test creation with a valid UUID."""
        valid_uuid = str(uuid.uuid4())
        session_id = SessionId(valid_uuid)
        assert session_id.value == valid_uuid

    def test_invalid_uuid_format(self):
        """Test rejection of invalid UUID format."""
        with pytest.raises(InvalidSessionIdError):
            SessionId("not-a-uuid")

    def test_invalid_empty_string(self):
        """Test rejection of empty string."""
        with pytest.raises(InvalidSessionIdError):
            SessionId("")

    def test_invalid_partial_uuid(self):
        """Test rejection of partial UUID."""
        with pytest.raises(InvalidSessionIdError):
            SessionId("123e4567-e89b-12d3")

    def test_generate_creates_valid_uuid(self):
        """Test that generate creates a valid UUID."""
        session_id = SessionId.generate()
        # Should not raise - validates UUID format
        uuid.UUID(session_id.value)

    def test_generate_creates_unique_ids(self):
        """Test that generate creates unique IDs."""
        ids = [SessionId.generate() for _ in range(100)]
        unique_values = set(s.value for s in ids)
        assert len(unique_values) == 100

    def test_str_representation(self):
        """Test string representation."""
        valid_uuid = str(uuid.uuid4())
        session_id = SessionId(valid_uuid)
        assert str(session_id) == valid_uuid

    def test_immutability(self):
        """Test that the value object is immutable."""
        session_id = SessionId.generate()
        with pytest.raises(AttributeError):
            session_id.value = str(uuid.uuid4())

    def test_equality(self):
        """Test equality comparison."""
        valid_uuid = str(uuid.uuid4())
        id1 = SessionId(valid_uuid)
        id2 = SessionId(valid_uuid)
        assert id1 == id2


class TestFilePath:
    """Tests for FilePath value object."""

    def test_valid_simple_path(self):
        """Test creation with a simple file path."""
        path = FilePath("main.py")
        assert path.value == "main.py"

    def test_valid_nested_path(self):
        """Test creation with a nested path."""
        path = FilePath("src/utils/helpers.py")
        assert path.value == "src/utils/helpers.py"

    def test_valid_path_with_dashes_and_underscores(self):
        """Test creation with dashes and underscores."""
        path = FilePath("src/my-module/my_file.py")
        assert path.value == "src/my-module/my_file.py"

    def test_invalid_empty_path(self):
        """Test rejection of empty path."""
        with pytest.raises(InvalidFilePathError):
            FilePath("")

    def test_invalid_whitespace_only(self):
        """Test rejection of whitespace-only path."""
        with pytest.raises(InvalidFilePathError):
            FilePath("   ")

    def test_invalid_path_traversal_double_dot(self):
        """Test rejection of path with '..'."""
        with pytest.raises(InvalidFilePathError):
            FilePath("../../../etc/passwd")

    def test_invalid_path_traversal_embedded(self):
        """Test rejection of path with embedded '..'."""
        with pytest.raises(InvalidFilePathError):
            FilePath("src/../secret/file.txt")

    def test_extension_property_python(self):
        """Test extension extraction for Python file."""
        path = FilePath("main.py")
        assert path.extension == ".py"

    def test_extension_property_javascript(self):
        """Test extension extraction for JavaScript file."""
        path = FilePath("app.js")
        assert path.extension == ".js"

    def test_extension_property_no_extension(self):
        """Test extension extraction for file without extension."""
        path = FilePath("Makefile")
        assert path.extension == ""

    def test_extension_property_multiple_dots(self):
        """Test extension extraction for file with multiple dots."""
        path = FilePath("archive.tar.gz")
        assert path.extension == ".gz"

    def test_filename_property(self):
        """Test filename extraction."""
        path = FilePath("src/utils/helpers.py")
        assert path.filename == "helpers.py"

    def test_filename_property_simple(self):
        """Test filename extraction for simple path."""
        path = FilePath("main.py")
        assert path.filename == "main.py"

    def test_directory_property(self):
        """Test directory extraction."""
        path = FilePath("src/utils/helpers.py")
        assert path.directory == "src/utils"

    def test_directory_property_simple(self):
        """Test directory extraction for simple path."""
        path = FilePath("main.py")
        assert path.directory == "."

    def test_str_representation(self):
        """Test string representation."""
        path = FilePath("src/main.py")
        assert str(path) == "src/main.py"

    def test_immutability(self):
        """Test that the value object is immutable."""
        path = FilePath("main.py")
        with pytest.raises(AttributeError):
            path.value = "other.py"

    def test_equality(self):
        """Test equality comparison."""
        path1 = FilePath("src/main.py")
        path2 = FilePath("src/main.py")
        assert path1 == path2
