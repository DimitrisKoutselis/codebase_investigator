from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from .chat_dtos import MessageDTO


class SessionDTO(BaseModel):
    """DTO representing a chat session."""

    id: str
    codebase_id: str
    title: Optional[str] = None
    message_count: int
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageDTO]] = None


class SessionListResponse(BaseModel):
    """Response DTO for listing sessions."""

    sessions: List[SessionDTO]
    total: int
