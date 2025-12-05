from dataclasses import dataclass
from typing import Protocol, AsyncIterator, Any

from src.domain.entities.chat_session import ChatSession
from src.domain.entities.message import Message
from src.domain.repositories.i_chat_session_repository import IChatSessionRepository
from src.domain.repositories.i_codebase_repository import ICodebaseRepository
from src.domain.value_objects.session_id import SessionId
from src.domain.exceptions.domain_exceptions import (
    CodebaseNotFoundError,
    CodebaseNotIndexedError,
)
from src.application.dtos.chat_dtos import ChatRequest, ChatResponse, MessageDTO
from src.application.interfaces.i_vector_store import IVectorStore
from src.application.interfaces.i_cache_service import ICacheService


class IAgentRunner(Protocol):
    """Protocol for the LangGraph agent runner."""

    async def run(
        self,
        query: str,
        conversation_history: list[dict[str, Any]],
        codebase_id: str,
    ) -> tuple[str, list[str]]:
        """Run the agent and return (response, source_files)."""
        ...

    def stream(
        self,
        query: str,
        conversation_history: list[dict[str, Any]],
        codebase_id: str,
    ) -> AsyncIterator[str]:
        """Stream the agent response."""
        ...


@dataclass
class SendMessageUseCase:
    """Use case for sending a message in a chat session."""

    session_repository: IChatSessionRepository
    codebase_repository: ICodebaseRepository
    vector_store: IVectorStore
    cache_service: ICacheService
    agent_runner: IAgentRunner

    async def execute(
        self,
        session_id: str,
        codebase_id: str,
        request: ChatRequest,
    ) -> ChatResponse:
        """Process a user message and generate a response.

        1. Validate codebase is ready
        2. Get or create chat session
        3. Add user message
        4. Run LangGraph agent
        5. Add assistant response
        6. Return response
        """
        # Validate codebase
        codebase = await self.codebase_repository.get_by_id(codebase_id)
        if not codebase:
            raise CodebaseNotFoundError(f"Codebase {codebase_id} not found")
        if not codebase.is_ready:
            raise CodebaseNotIndexedError(f"Codebase {codebase_id} is not ready")

        # Get or create session
        sid = SessionId(session_id)
        session = await self.session_repository.get_by_id(sid)

        if not session:
            session = ChatSession(id=sid, codebase_id=codebase_id)

        # Add user message
        user_message = Message.user_message(request.message)
        session.add_message(user_message)

        # Check cache for similar queries
        cache_key = f"response:{codebase_id}:{hash(request.message)}"
        cached = await self.cache_service.get(cache_key)

        if cached and not request.stream:
            response_content, sources = cached["response"], cached["sources"]
        else:
            # Run agent
            response_content, sources = await self.agent_runner.run(
                query=request.message,
                conversation_history=session.get_conversation_history()[:-1],
                codebase_id=codebase_id,
            )

            # Cache the response
            await self.cache_service.set(
                cache_key,
                {"response": response_content, "sources": sources},
                ttl_seconds=3600,
            )

        # Add assistant message
        assistant_message = Message.assistant_message(
            content=response_content,
            metadata={"sources": sources},
        )
        session.add_message(assistant_message)

        # Save session
        await self.session_repository.save(session)

        return ChatResponse(
            session_id=str(session.id),
            message=MessageDTO(
                role="assistant",
                content=response_content,
                timestamp=assistant_message.timestamp,
                metadata=assistant_message.metadata,
            ),
            sources=sources,
        )
