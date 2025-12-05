from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.chat_session import ChatSession
from ..value_objects.session_id import SessionId


class IChatSessionRepository(ABC):
    """Abstract repository interface for ChatSession persistence."""

    @abstractmethod
    async def get_by_id(self, session_id: SessionId) -> Optional[ChatSession]:
        """Retrieve a chat session by its ID."""
        pass

    @abstractmethod
    async def save(self, session: ChatSession) -> None:
        """Persist a chat session."""
        pass

    @abstractmethod
    async def delete(self, session_id: SessionId) -> None:
        """Delete a chat session."""
        pass

    @abstractmethod
    async def list_by_codebase(self, codebase_id: str) -> List[ChatSession]:
        """List all sessions for a specific codebase."""
        pass
