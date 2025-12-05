from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass


@dataclass
class CodeChunk:
    """Represents a chunk of code for embedding."""

    content: str
    file_path: str
    start_line: int
    end_line: int
    metadata: dict | None = None


@dataclass
class SearchResult:
    """Represents a search result from the vector store."""

    chunk: CodeChunk
    score: float


class IVectorStore(ABC):
    """Interface for vector store operations."""

    @abstractmethod
    async def create_index(self, codebase_id: str) -> None:
        """Create a new index for a codebase."""
        pass

    @abstractmethod
    async def add_chunks(self, codebase_id: str, chunks: List[CodeChunk]) -> None:
        """Add code chunks to the vector store."""
        pass

    @abstractmethod
    async def search(
        self, codebase_id: str, query: str, top_k: int = 5
    ) -> List[SearchResult]:
        """Search for relevant code chunks."""
        pass

    @abstractmethod
    async def delete_index(self, codebase_id: str) -> None:
        """Delete an index for a codebase."""
        pass
