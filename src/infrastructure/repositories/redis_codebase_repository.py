import json
from typing import List, Optional, Any
from datetime import datetime

import redis.asyncio as aioredis

from src.domain.entities.codebase import Codebase, IndexingStatus
from src.domain.repositories.i_codebase_repository import ICodebaseRepository
from src.domain.value_objects.repo_url import RepoURL


class RedisCodebaseRepository(ICodebaseRepository):
    """Redis-based repository for codebases."""

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

    def _serialize_codebase(self, codebase: Codebase) -> str:
        """Serialize codebase to JSON."""
        return json.dumps(
            {
                "id": codebase.id,
                "repo_url": str(codebase.repo_url),
                "local_path": codebase.local_path,
                "indexing_status": codebase.indexing_status.value,
                "indexed_at": (
                    codebase.indexed_at.isoformat() if codebase.indexed_at else None
                ),
                "file_count": codebase.file_count,
                "error_message": codebase.error_message,
                "created_at": codebase.created_at.isoformat(),
            }
        )

    def _deserialize_codebase(self, data: str) -> Codebase:
        """Deserialize codebase from JSON."""
        obj = json.loads(data)
        return Codebase(
            id=obj["id"],
            repo_url=RepoURL(obj["repo_url"]),
            local_path=obj["local_path"],
            indexing_status=IndexingStatus(obj["indexing_status"]),
            indexed_at=(
                datetime.fromisoformat(obj["indexed_at"]) if obj["indexed_at"] else None
            ),
            file_count=obj["file_count"],
            error_message=obj.get("error_message"),
            created_at=datetime.fromisoformat(obj["created_at"]),
        )

    async def get_by_id(self, codebase_id: str) -> Optional[Codebase]:
        """Retrieve a codebase by its ID."""
        client = await self._get_client()
        data = await client.get(f"codebase:{codebase_id}")
        if data:
            return self._deserialize_codebase(data)
        return None

    async def get_by_url(self, repo_url: RepoURL) -> Optional[Codebase]:
        """Retrieve a codebase by its repository URL."""
        client = await self._get_client()

        # Look up by URL index
        codebase_id = await client.get(f"codebase:url:{repo_url}")
        if codebase_id:
            return await self.get_by_id(codebase_id)
        return None

    async def save(self, codebase: Codebase) -> None:
        """Persist a codebase."""
        client = await self._get_client()

        # Save codebase data
        await client.set(
            f"codebase:{codebase.id}",
            self._serialize_codebase(codebase),
        )

        # Create URL index
        await client.set(
            f"codebase:url:{codebase.repo_url}",
            codebase.id,
        )

        # Add to list of all codebases
        await client.sadd("codebases:all", codebase.id)

    async def delete(self, codebase_id: str) -> None:
        """Delete a codebase."""
        client = await self._get_client()

        # Get codebase to find URL
        codebase = await self.get_by_id(codebase_id)
        if codebase:
            await client.delete(f"codebase:url:{codebase.repo_url}")

        await client.delete(f"codebase:{codebase_id}")
        await client.srem("codebases:all", codebase_id)

    async def list_all(self) -> List[Codebase]:
        """List all indexed codebases."""
        client = await self._get_client()

        codebase_ids: set[Any] = await client.smembers("codebases:all")
        codebases = []

        for cid in codebase_ids:
            data = await client.get(f"codebase:{cid}")
            if data:
                codebases.append(self._deserialize_codebase(data))

        # Sort by created_at descending
        codebases.sort(key=lambda c: c.created_at, reverse=True)
        return codebases
