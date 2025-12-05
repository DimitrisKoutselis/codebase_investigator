"""
LangGraph RAG Workflow for Codebase Q&A.

This module defines the main LangGraph workflow that:
1. Takes a user query
2. Retrieves relevant code from the vector store (via MCP or directly)
3. Generates a response using the LLM

The graph uses MCP tools when available, falling back to direct tool calls.
"""

from typing import TypedDict, Annotated, Sequence, List, AsyncIterator, Any
from dataclasses import dataclass

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from src.application.interfaces.i_vector_store import IVectorStore
from src.infrastructure.mcp.client.mcp_client import MCPClientManager


class GraphState(TypedDict):
    """State maintained throughout the graph execution."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    codebase_id: str
    retrieved_context: str
    source_files: List[str]


SYSTEM_PROMPT = """You are a helpful code assistant that answers questions about a specific codebase.

You have access to the following retrieved code context:

{context}

Instructions:
- Answer the user's question based on the provided code context
- Be specific and reference actual code when relevant
- If the context doesn't contain enough information, say so
- Format code snippets using markdown code blocks
- Keep responses concise but complete
- Do NOT output markdown. Output simple plain text
"""


@dataclass
class RAGGraph:
    """LangGraph-based RAG workflow for codebase Q&A."""

    vector_store: IVectorStore
    mcp_client: MCPClientManager | None
    gemini_api_key: str
    model_name: str = "gemini-2.5-flash"

    def __post_init__(self) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.gemini_api_key,
            temperature=0.3,
        )
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Build the LangGraph workflow."""

        workflow: StateGraph[GraphState] = StateGraph(GraphState)

        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    async def _retrieve_node(self, state: GraphState) -> dict[str, Any]:
        """Retrieve relevant code from vector store."""
        query = state["query"]
        codebase_id = state["codebase_id"]

        if self.mcp_client:
            try:
                await self.mcp_client.connect("codebase")
                result = await self.mcp_client.call_tool(
                    "search_code",
                    {"query": query, "top_k": 5},
                )
                await self.mcp_client.disconnect()

                return {
                    "retrieved_context": result or "No relevant code found.",
                    "source_files": [],
                }
            except Exception:
                pass

        results = await self.vector_store.search(codebase_id, query, top_k=5)

        if not results:
            return {
                "retrieved_context": "No relevant code found in the repository.",
                "source_files": [],
            }

        context_parts = []
        source_files: list[str] = []

        for i, result in enumerate(results, 1):
            chunk = result.chunk
            context_parts.append(
                f"### File: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})\n"
                f"```\n{chunk.content}\n```"
            )
            if chunk.file_path not in source_files:
                source_files.append(chunk.file_path)

        return {
            "retrieved_context": "\n\n".join(context_parts),
            "source_files": source_files,
        }

    async def _generate_node(self, state: GraphState) -> dict[str, Any]:
        """Generate response using the LLM."""
        query = state["query"]
        context = state["retrieved_context"]
        messages: list[BaseMessage] = list(state.get("messages", []))

        system_message = SystemMessage(content=SYSTEM_PROMPT.format(context=context))

        messages.append(HumanMessage(content=query))

        all_messages: list[BaseMessage] = [system_message] + messages
        response = await self._llm.ainvoke(all_messages)

        return {
            "messages": [response],
        }

    async def run(
        self,
        query: str,
        conversation_history: list[dict[str, Any]],
        codebase_id: str,
    ) -> tuple[str, list[str]]:
        """Run the RAG workflow and return (response, source_files)."""

        messages: list[BaseMessage] = []
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        initial_state: GraphState = {
            "messages": messages,
            "query": query,
            "codebase_id": codebase_id,
            "retrieved_context": "",
            "source_files": [],
        }

        result = await self._graph.ainvoke(initial_state)

        response_message = result["messages"][-1]
        response_content = (
            response_message.content
            if hasattr(response_message, "content")
            else str(response_message)
        )

        return str(response_content), result.get("source_files", [])

    async def stream(
        self,
        query: str,
        conversation_history: list[dict[str, Any]],
        codebase_id: str,
    ) -> AsyncIterator[str]:
        """Stream the RAG workflow response."""

        messages: list[BaseMessage] = []
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        initial_state: GraphState = {
            "messages": messages,
            "query": query,
            "codebase_id": codebase_id,
            "retrieved_context": "",
            "source_files": [],
        }

        async for event in self._graph.astream_events(initial_state, version="v1"):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield str(chunk.content)


def create_rag_graph(
    vector_store: IVectorStore,
    mcp_client: MCPClientManager | None,
    gemini_api_key: str,
) -> RAGGraph:
    """Factory function to create a RAG graph."""
    return RAGGraph(
        vector_store=vector_store,
        mcp_client=mcp_client,
        gemini_api_key=gemini_api_key,
    )
