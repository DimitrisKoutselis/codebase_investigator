from pydantic import BaseModel, HttpUrl
from enum import Enum
from typing import Optional
from datetime import datetime


class IngestStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestRequest(BaseModel):
    """Request DTO for ingesting a GitHub repository."""

    repo_url: HttpUrl

    class Config:
        json_schema_extra = {"example": {"repo_url": "https://github.com/owner/repo"}}


class IngestResponse(BaseModel):
    """Response DTO after initiating or checking ingestion."""

    codebase_id: str
    repo_url: str
    status: IngestStatus
    file_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    indexed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "codebase_id": "abc123",
                "repo_url": "https://github.com/owner/repo",
                "status": "completed",
                "file_count": 42,
                "created_at": "2024-01-15T10:30:00Z",
                "indexed_at": "2024-01-15T10:32:00Z",
            }
        }
