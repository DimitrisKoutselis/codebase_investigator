class DomainError(Exception):
    """Base exception for all domain-level errors."""

    pass


class InvalidRepositoryURLError(DomainError):
    """Raised when a repository URL is not a valid GitHub URL."""

    pass


class InvalidSessionIdError(DomainError):
    """Raised when a session ID is not in valid UUID format."""

    pass


class InvalidFilePathError(DomainError):
    """Raised when a file path is invalid or potentially dangerous."""

    pass


class CodebaseNotFoundError(DomainError):
    """Raised when a requested codebase does not exist."""

    pass


class CodebaseNotIndexedError(DomainError):
    """Raised when trying to query a codebase that hasn't been indexed."""

    pass


class SessionNotFoundError(DomainError):
    """Raised when a requested chat session does not exist."""

    pass
