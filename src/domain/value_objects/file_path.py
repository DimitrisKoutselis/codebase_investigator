from dataclasses import dataclass
from pathlib import Path

from ..exceptions.domain_exceptions import InvalidFilePathError


@dataclass(frozen=True)
class FilePath:
    """Immutable value object representing a file path within a repository."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value.strip() == "":
            raise InvalidFilePathError("File path cannot be empty")

        # Prevent path traversal attacks
        if ".." in self.value:
            raise InvalidFilePathError(f"Path traversal not allowed: {self.value}")

    @property
    def extension(self) -> str:
        """Get the file extension."""
        return Path(self.value).suffix

    @property
    def filename(self) -> str:
        """Get the filename without directory."""
        return Path(self.value).name

    @property
    def directory(self) -> str:
        """Get the parent directory path."""
        return str(Path(self.value).parent)

    def __str__(self) -> str:
        return self.value
