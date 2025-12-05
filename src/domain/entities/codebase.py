from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from ..value_objects.repo_url import RepoURL


class IndexingStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Codebase:
    """Represents an ingested GitHub repository."""

    id: str
    repo_url: RepoURL
    local_path: str
    indexing_status: IndexingStatus = IndexingStatus.PENDING
    indexed_at: Optional[datetime] = None
    file_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def mark_indexing_started(self) -> None:
        self.indexing_status = IndexingStatus.IN_PROGRESS

    def mark_indexing_completed(self, file_count: int) -> None:
        self.indexing_status = IndexingStatus.COMPLETED
        self.indexed_at = datetime.utcnow()
        self.file_count = file_count

    def mark_indexing_failed(self, error: str) -> None:
        self.indexing_status = IndexingStatus.FAILED
        self.error_message = error

    @property
    def is_ready(self) -> bool:
        return self.indexing_status == IndexingStatus.COMPLETED
