from abc import ABC, abstractmethod
from typing import List

from src.domain.value_objects.repo_url import RepoURL


class IGitService(ABC):
    """Interface for Git operations."""

    @abstractmethod
    async def clone_repository(self, repo_url: RepoURL, target_path: str) -> str:
        """Clone a repository and return the local path."""
        pass

    @abstractmethod
    async def list_files(
        self, local_path: str, extensions: List[str] | None = None
    ) -> List[str]:
        """List all files in a cloned repository, optionally filtered by extension."""
        pass

    @abstractmethod
    async def read_file(self, local_path: str, file_path: str) -> str:
        """Read contents of a specific file."""
        pass
