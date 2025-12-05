from dataclasses import dataclass

from src.domain.repositories.i_chat_session_repository import IChatSessionRepository
from src.domain.value_objects.session_id import SessionId
from src.domain.exceptions.domain_exceptions import SessionNotFoundError
from src.application.dtos.session_dtos import SessionDTO
from src.application.dtos.chat_dtos import MessageDTO


@dataclass
class GetSessionUseCase:
    """Use case for retrieving a chat session."""

    session_repository: IChatSessionRepository

    async def execute(
        self,
        session_id: str,
        include_messages: bool = True,
    ) -> SessionDTO:
        """Get a session by ID.

        Args:
            session_id: The session ID to retrieve
            include_messages: Whether to include full message history

        Returns:
            SessionDTO with session details

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        sid = SessionId(session_id)
        session = await self.session_repository.get_by_id(sid)

        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found")

        messages = None
        if include_messages:
            messages = [
                MessageDTO(
                    role=msg.role.value,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.metadata,
                )
                for msg in session.messages
            ]

        return SessionDTO(
            id=str(session.id),
            codebase_id=session.codebase_id,
            title=session.title,
            message_count=session.message_count,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=messages,
        )
