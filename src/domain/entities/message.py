from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class Message:
    """Represents a single message in a chat conversation."""

    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[dict] = None

    @classmethod
    def user_message(cls, content: str) -> "Message":
        return cls(role=MessageRole.USER, content=content, timestamp=datetime.utcnow())

    @classmethod
    def assistant_message(
        cls, content: str, metadata: Optional[dict] = None
    ) -> "Message":
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )
