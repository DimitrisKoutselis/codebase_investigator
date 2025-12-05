from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.codebase import Codebase
from ..value_objects.repo_url import RepoURL


class ICodebaseRepository(ABC):
    """Abstract repository interface for Codebase persistence."""

    @abstractmethod
    async def get_by_id(self, codebase_id: str) -> Optional[Codebase]:
        """Retrieve a codebase by its ID."""
        pass

    @abstractmethod
    async def get_by_url(self, repo_url: RepoURL) -> Optional[Codebase]:
        """Retrieve a codebase by its repository URL."""
        pass

    @abstractmethod
    async def save(self, codebase: Codebase) -> None:
        """Persist a codebase."""
        pass

    @abstractmethod
    async def delete(self, codebase_id: str) -> None:
        """Delete a codebase."""
        pass

    @abstractmethod
    async def list_all(self) -> List[Codebase]:
        """List all indexed codebases."""
        pass
