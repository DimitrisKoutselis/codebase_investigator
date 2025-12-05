from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class MessageDTO(BaseModel):
    """DTO representing a single chat message."""

    role: str  # "user", "assistant", or "system"
    content: str
    timestamp: datetime
    metadata: Optional[dict] = None


class ChatRequest(BaseModel):
    """Request DTO for sending a chat message."""

    message: str
    stream: bool = False

    class Config:
        json_schema_extra = {
            "example": {"message": "What does the main function do?", "stream": False}
        }


class ChatResponse(BaseModel):
    """Response DTO for a chat message."""

    session_id: str
    message: MessageDTO
    sources: Optional[List[str]] = None  # File paths used for context

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "uuid-here",
                "message": {
                    "role": "assistant",
                    "content": "The main function initializes the application...",
                    "timestamp": "2024-01-15T10:30:00Z",
                },
                "sources": ["src/main.py", "src/app.py"],
            }
        }
