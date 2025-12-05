"""
Unit tests for domain exceptions.
"""

import pytest

from src.domain.exceptions.domain_exceptions import (
    DomainError,
    InvalidRepositoryURLError,
    InvalidSessionIdError,
    InvalidFilePathError,
    CodebaseNotFoundError,
    CodebaseNotIndexedError,
    SessionNotFoundError,
)


class TestDomainExceptions:
    """Tests for domain exception hierarchy."""

    def test_domain_error_is_base(self):
        """Test that DomainError is the base exception."""
        error = DomainError("Base error")
        assert isinstance(error, Exception)
        assert str(error) == "Base error"

    def test_invalid_repository_url_error(self):
        """Test InvalidRepositoryURLError."""
        error = InvalidRepositoryURLError("Invalid URL: example.com")

        assert isinstance(error, DomainError)
        assert isinstance(error, Exception)
        assert str(error) == "Invalid URL: example.com"

    def test_invalid_session_id_error(self):
        """Test InvalidSessionIdError."""
        error = InvalidSessionIdError("Invalid session ID: abc")

        assert isinstance(error, DomainError)
        assert str(error) == "Invalid session ID: abc"

    def test_invalid_file_path_error(self):
        """Test InvalidFilePathError."""
        error = InvalidFilePathError("Path traversal detected")

        assert isinstance(error, DomainError)
        assert str(error) == "Path traversal detected"

    def test_codebase_not_found_error(self):
        """Test CodebaseNotFoundError."""
        error = CodebaseNotFoundError("Codebase cb-123 not found")

        assert isinstance(error, DomainError)
        assert str(error) == "Codebase cb-123 not found"

    def test_codebase_not_indexed_error(self):
        """Test CodebaseNotIndexedError."""
        error = CodebaseNotIndexedError("Codebase cb-123 not indexed yet")

        assert isinstance(error, DomainError)
        assert str(error) == "Codebase cb-123 not indexed yet"

    def test_session_not_found_error(self):
        """Test SessionNotFoundError."""
        error = SessionNotFoundError("Session sess-456 not found")

        assert isinstance(error, DomainError)
        assert str(error) == "Session sess-456 not found"

    def test_exceptions_can_be_raised_and_caught(self):
        """Test that exceptions can be raised and caught properly."""
        with pytest.raises(InvalidRepositoryURLError) as exc_info:
            raise InvalidRepositoryURLError("Test error")

        assert "Test error" in str(exc_info.value)

    def test_catch_by_base_class(self):
        """Test that exceptions can be caught by base class."""
        with pytest.raises(DomainError):
            raise InvalidRepositoryURLError("Test")

        with pytest.raises(DomainError):
            raise CodebaseNotFoundError("Test")

        with pytest.raises(DomainError):
            raise SessionNotFoundError("Test")

    def test_exception_with_no_message(self):
        """Test exception with no message."""
        error = DomainError()
        assert str(error) == ""

    def test_exception_inheritance_chain(self):
        """Test the full inheritance chain."""
        error = CodebaseNotFoundError("Not found")

        assert isinstance(error, CodebaseNotFoundError)
        assert isinstance(error, DomainError)
        assert isinstance(error, Exception)
        assert isinstance(error, BaseException)
