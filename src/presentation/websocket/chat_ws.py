"""
WebSocket Chat Handler.

Provides real-time streaming chat with the codebase.
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_message(self, session_id: str, message: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)


manager = ConnectionManager()


@router.websocket("/ws/chat/{codebase_id}/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    codebase_id: str,
    session_id: str,
):
    """WebSocket endpoint for real-time chat.

    Messages are JSON objects:
    - Client sends: {"message": "user query"}
    - Server sends: {"type": "chunk", "content": "..."}
    - Server sends: {"type": "done", "sources": [...]}
    - Server sends: {"type": "error", "message": "..."}
    """
    await manager.connect(session_id, websocket)

    try:
        # Get dependencies (simplified - in production, use proper DI)
        from src.infrastructure.config.settings import get_settings
        from src.infrastructure.vector_store.faiss_store import FAISSVectorStore
        from src.infrastructure.mcp.client.mcp_client import MCPClientManager
        from src.infrastructure.llm.graph.rag_graph import create_rag_graph

        settings = get_settings()
        vector_store = FAISSVectorStore(
            index_path=settings.faiss_index_path,
            gemini_api_key=settings.gemini_api_key,
        )
        mcp_client = MCPClientManager()
        rag_graph = create_rag_graph(
            vector_store=vector_store,
            mcp_client=mcp_client,
            gemini_api_key=settings.gemini_api_key,
        )

        conversation_history = []

        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            if not user_message:
                continue

            # Add to history
            conversation_history.append({"role": "user", "content": user_message})

            try:
                # Stream response
                full_response = ""
                async for chunk in rag_graph.stream(
                    query=user_message,
                    conversation_history=conversation_history[:-1],
                    codebase_id=codebase_id,
                ):
                    full_response += chunk
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "chunk",
                                "content": chunk,
                            }
                        )
                    )

                # Add assistant response to history
                conversation_history.append(
                    {
                        "role": "assistant",
                        "content": full_response,
                    }
                )

                # Send done signal
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "done",
                            "sources": [],
                        }
                    )
                )

            except Exception as e:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": str(e),
                        }
                    )
                )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
