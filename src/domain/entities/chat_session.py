from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .message import Message
from ..value_objects.session_id import SessionId


@dataclass
class ChatSession:
    """Represents a chat conversation about a specific codebase."""

    id: SessionId
    codebase_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    title: Optional[str] = None

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

        # Auto-generate title from first user message
        if self.title is None and message.role.value == "user":
            self.title = (
                message.content[:50] + "..."
                if len(message.content) > 50
                else message.content
            )

    def get_conversation_history(self) -> List[dict]:
        """Returns messages in a format suitable for LLM context."""
        return [
            {"role": msg.role.value, "content": msg.content} for msg in self.messages
        ]

    @property
    def message_count(self) -> int:
        return len(self.messages)
