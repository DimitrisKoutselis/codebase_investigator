import json
from typing import List, Optional, Any
from datetime import datetime

import redis.asyncio as aioredis

from src.domain.entities.chat_session import ChatSession
from src.domain.entities.message import Message, MessageRole
from src.domain.repositories.i_chat_session_repository import IChatSessionRepository
from src.domain.value_objects.session_id import SessionId


class RedisSessionRepository(IChatSessionRepository):
    """Redis-based repository for chat sessions."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client: Any = None

    async def _get_client(self) -> Any:
        if self._client is None:
            self._client = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    def _serialize_session(self, session: ChatSession) -> str:
        """Serialize session to JSON."""
        return json.dumps(
            {
                "id": str(session.id),
                "codebase_id": session.codebase_id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "messages": [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "metadata": msg.metadata,
                    }
                    for msg in session.messages
                ],
            }
        )

    def _deserialize_session(self, data: str) -> ChatSession:
        """Deserialize session from JSON."""
        obj = json.loads(data)
        messages = [
            Message(
                role=MessageRole(msg["role"]),
                content=msg["content"],
                timestamp=datetime.fromisoformat(msg["timestamp"]),
                metadata=msg.get("metadata"),
            )
            for msg in obj["messages"]
        ]
        return ChatSession(
            id=SessionId(obj["id"]),
            codebase_id=obj["codebase_id"],
            messages=messages,
            created_at=datetime.fromisoformat(obj["created_at"]),
            updated_at=datetime.fromisoformat(obj["updated_at"]),
            title=obj.get("title"),
        )

    async def get_by_id(self, session_id: SessionId) -> Optional[ChatSession]:
        """Retrieve a chat session by its ID."""
        client = await self._get_client()
        data = await client.get(f"session:{session_id}")
        if data:
            return self._deserialize_session(data)
        return None

    async def save(self, session: ChatSession) -> None:
        """Persist a chat session."""
        client = await self._get_client()

        # Save session
        await client.set(
            f"session:{session.id}",
            self._serialize_session(session),
        )

        # Add to codebase's session set
        await client.sadd(
            f"codebase:{session.codebase_id}:sessions",
            str(session.id),
        )

    async def delete(self, session_id: SessionId) -> None:
        """Delete a chat session."""
        client = await self._get_client()

        # Get session to find codebase_id
        session = await self.get_by_id(session_id)
        if session:
            await client.srem(
                f"codebase:{session.codebase_id}:sessions",
                str(session_id),
            )

        await client.delete(f"session:{session_id}")

    async def list_by_codebase(self, codebase_id: str) -> List[ChatSession]:
        """List all sessions for a specific codebase."""
        client = await self._get_client()

        session_ids: set[Any] = await client.smembers(
            f"codebase:{codebase_id}:sessions"
        )
        sessions = []

        for sid in session_ids:
            data = await client.get(f"session:{sid}")
            if data:
                sessions.append(self._deserialize_session(data))

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions
