import uuid
from dataclasses import dataclass

from src.domain.entities.codebase import Codebase
from src.domain.repositories.i_codebase_repository import ICodebaseRepository
from src.domain.value_objects.repo_url import RepoURL
from src.application.interfaces.i_git_service import IGitService
from src.application.interfaces.i_vector_store import IVectorStore, CodeChunk
from src.application.dtos.ingest_dtos import IngestRequest, IngestResponse, IngestStatus


@dataclass
class IngestCodebaseUseCase:
    """Use case for ingesting a GitHub repository into the system."""

    codebase_repository: ICodebaseRepository
    git_service: IGitService
    vector_store: IVectorStore

    async def execute(self, request: IngestRequest) -> IngestResponse:
        """Ingest a GitHub repository.

        1. Validate and parse the repository URL
        2. Check if already ingested
        3. Clone the repository
        4. Index code into vector store
        5. Save codebase metadata
        """
        repo_url = RepoURL(str(request.repo_url))

        # Check if already ingested
        existing = await self.codebase_repository.get_by_url(repo_url)
        if existing and existing.is_ready:
            return IngestResponse(
                codebase_id=existing.id,
                repo_url=str(existing.repo_url),
                status=IngestStatus(existing.indexing_status.value),
                file_count=existing.file_count,
                created_at=existing.created_at,
                indexed_at=existing.indexed_at,
            )

        # Create new codebase entity
        codebase_id = str(uuid.uuid4())
        local_path = f"./repos/{codebase_id}"

        codebase = Codebase(
            id=codebase_id,
            repo_url=repo_url,
            local_path=local_path,
        )

        try:
            # Clone repository
            codebase.mark_indexing_started()
            await self.codebase_repository.save(codebase)

            await self.git_service.clone_repository(repo_url, local_path)

            # Get files and create chunks
            files = await self.git_service.list_files(
                local_path,
                extensions=[".py", ".js", ".ts", ".md", ".json", ".yaml", ".yml"],
            )

            chunks = []
            for file_path in files:
                content = await self.git_service.read_file(local_path, file_path)
                # Simple chunking - can be improved
                chunks.append(
                    CodeChunk(
                        content=content,
                        file_path=file_path,
                        start_line=1,
                        end_line=content.count("\n") + 1,
                    )
                )

            # Index into vector store
            await self.vector_store.create_index(codebase_id)
            await self.vector_store.add_chunks(codebase_id, chunks)

            # Mark as completed
            codebase.mark_indexing_completed(len(files))
            await self.codebase_repository.save(codebase)

            return IngestResponse(
                codebase_id=codebase.id,
                repo_url=str(codebase.repo_url),
                status=IngestStatus.COMPLETED,
                file_count=codebase.file_count,
                created_at=codebase.created_at,
                indexed_at=codebase.indexed_at,
            )

        except Exception as e:
            codebase.mark_indexing_failed(str(e))
            await self.codebase_repository.save(codebase)

            return IngestResponse(
                codebase_id=codebase.id,
                repo_url=str(codebase.repo_url),
                status=IngestStatus.FAILED,
                error_message=str(e),
                created_at=codebase.created_at,
            )
