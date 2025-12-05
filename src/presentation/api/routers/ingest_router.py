"""
Ingestion Router - Endpoints for adding GitHub repositories.
"""

from fastapi import APIRouter, HTTPException, status

from src.application.dtos.ingest_dtos import IngestRequest, IngestResponse, IngestStatus
from src.domain.exceptions.domain_exceptions import InvalidRepositoryURLError
from src.presentation.api.dependencies import IngestUseCaseDep, CodebaseRepositoryDep

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post(
    "",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a GitHub repository",
    description="Clone and index a GitHub repository for querying.",
)
async def ingest_repository(
    request: IngestRequest,
    use_case: IngestUseCaseDep,
):
    """Ingest a GitHub repository.

    This endpoint:
    1. Validates the GitHub URL
    2. Clones the repository
    3. Indexes code into the vector store
    4. Returns the codebase ID for future queries
    """
    try:
        result = await use_case.execute(request)
        return result
    except InvalidRepositoryURLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest repository: {str(e)}",
        )


@router.get(
    "/{codebase_id}",
    response_model=IngestResponse,
    summary="Get ingestion status",
    description="Check the status of a repository ingestion.",
)
async def get_ingestion_status(
    codebase_id: str,
    codebase_repository: CodebaseRepositoryDep,
):
    """Get the status of a repository ingestion."""
    codebase = await codebase_repository.get_by_id(codebase_id)

    if not codebase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Codebase {codebase_id} not found",
        )

    return IngestResponse(
        codebase_id=codebase.id,
        repo_url=str(codebase.repo_url),
        status=IngestStatus(codebase.indexing_status.value),
        file_count=codebase.file_count,
        error_message=codebase.error_message,
        created_at=codebase.created_at,
        indexed_at=codebase.indexed_at,
    )


@router.get(
    "",
    response_model=list[IngestResponse],
    summary="List all codebases",
    description="Get a list of all ingested repositories.",
)
async def list_codebases(
    codebase_repository: CodebaseRepositoryDep,
):
    """List all ingested codebases."""
    codebases = await codebase_repository.list_all()

    return [
        IngestResponse(
            codebase_id=cb.id,
            repo_url=str(cb.repo_url),
            status=IngestStatus(cb.indexing_status.value),
            file_count=cb.file_count,
            error_message=cb.error_message,
            created_at=cb.created_at,
            indexed_at=cb.indexed_at,
        )
        for cb in codebases
    ]
