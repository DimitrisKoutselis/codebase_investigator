import re
from dataclasses import dataclass

from ..exceptions.domain_exceptions import InvalidRepositoryURLError


@dataclass(frozen=True)
class RepoURL:
    """Immutable value object representing a valid GitHub repository URL."""

    value: str

    GITHUB_PATTERN = re.compile(
        r"^https?://github\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?/?$"
    )

    def __post_init__(self) -> None:
        if not self.GITHUB_PATTERN.match(self.value):
            raise InvalidRepositoryURLError(
                f"Invalid GitHub repository URL: {self.value}"
            )

    @property
    def owner(self) -> str:
        """Extract repository owner from URL."""
        parts = self.value.rstrip("/").rstrip(".git").split("/")
        return parts[-2]

    @property
    def repo_name(self) -> str:
        """Extract repository name from URL."""
        parts = self.value.rstrip("/").rstrip(".git").split("/")
        return parts[-1]

    @property
    def clone_url(self) -> str:
        """Return URL suitable for git clone."""
        url = self.value.rstrip("/")
        if not url.endswith(".git"):
            url += ".git"
        return url

    def __str__(self) -> str:
        return self.value
