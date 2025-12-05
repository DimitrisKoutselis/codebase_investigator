"""
Chat Router - Endpoints for chatting with a codebase.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.application.dtos.chat_dtos import ChatRequest, ChatResponse
from src.domain.exceptions.domain_exceptions import (
    CodebaseNotFoundError,
    CodebaseNotIndexedError,
)
from src.presentation.api.dependencies import SendMessageUseCaseDep, RAGGraphDep

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/{codebase_id}/{session_id}",
    response_model=ChatResponse,
    summary="Send a message",
    description="Send a message to chat with a codebase.",
)
async def send_message(
    codebase_id: str,
    session_id: str,
    request: ChatRequest,
    use_case: SendMessageUseCaseDep,
):
    """Send a message to the chatbot.

    This endpoint:
    1. Validates the codebase exists and is indexed
    2. Gets or creates a chat session
    3. Processes the message through the RAG pipeline
    4. Returns the assistant's response
    """
    try:
        result = await use_case.execute(
            session_id=session_id,
            codebase_id=codebase_id,
            request=request,
        )
        return result
    except CodebaseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except CodebaseNotIndexedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.post(
    "/{codebase_id}/{session_id}/stream",
    summary="Stream a response",
    description="Send a message and stream the response.",
)
async def stream_message(
    codebase_id: str,
    session_id: str,
    request: ChatRequest,
    rag_graph: RAGGraphDep,
):
    """Stream a response from the chatbot.

    Returns a Server-Sent Events stream of the response.
    """

    async def generate():
        async for chunk in rag_graph.stream(
            query=request.message,
            conversation_history=[],
            codebase_id=codebase_id,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
