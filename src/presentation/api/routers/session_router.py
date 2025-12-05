"""
Session Router - Endpoints for managing chat sessions.
"""

from fastapi import APIRouter, HTTPException, status

from src.application.dtos.session_dtos import SessionDTO, SessionListResponse
from src.domain.exceptions.domain_exceptions import SessionNotFoundError
from src.presentation.api.dependencies import (
    GetSessionUseCaseDep,
    SessionRepositoryDep,
    CodebaseRepositoryDep,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get(
    "/{session_id}",
    response_model=SessionDTO,
    summary="Get a session",
    description="Retrieve a chat session with its message history.",
)
async def get_session(
    session_id: str,
    use_case: GetSessionUseCaseDep,
    include_messages: bool = True,
):
    """Get a chat session by ID."""
    try:
        result = await use_case.execute(
            session_id=session_id,
            include_messages=include_messages,
        )
        return result
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/codebase/{codebase_id}",
    response_model=SessionListResponse,
    summary="List sessions for a codebase",
    description="Get all chat sessions for a specific codebase.",
)
async def list_sessions(
    codebase_id: str,
    session_repository: SessionRepositoryDep,
    codebase_repository: CodebaseRepositoryDep,
):
    """List all sessions for a codebase."""
    # Verify codebase exists
    codebase = await codebase_repository.get_by_id(codebase_id)
    if not codebase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Codebase {codebase_id} not found",
        )

    sessions = await session_repository.list_by_codebase(codebase_id)

    return SessionListResponse(
        sessions=[
            SessionDTO(
                id=str(s.id),
                codebase_id=s.codebase_id,
                title=s.title,
                message_count=s.message_count,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
    description="Delete a chat session and its history.",
)
async def delete_session(
    session_id: str,
    session_repository: SessionRepositoryDep,
):
    """Delete a chat session."""
    from src.domain.value_objects.session_id import SessionId

    try:
        sid = SessionId(session_id)
        await session_repository.delete(sid)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
