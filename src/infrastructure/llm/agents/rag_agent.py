"""
RAG Agent with MCP Tool Integration.

This agent uses LangGraph's ReAct pattern to:
1. Reason about the user's query
2. Decide which tools to use (via MCP)
3. Execute tools and synthesize a response

The agent can use tools from MCP servers dynamically.
"""

from typing import Any
from dataclasses import dataclass

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from src.application.interfaces.i_vector_store import IVectorStore
from src.infrastructure.mcp.client.mcp_client import MCPClientManager


AGENT_SYSTEM_PROMPT = """You are a helpful code assistant that can search and analyze codebases.

You have access to tools for:
- Searching code semantically
- Reading files
- Listing repository structure

When answering questions:
1. First search for relevant code if needed
2. Read specific files for more context
3. Provide clear, concise answers with code references
4. Use markdown formatting for code snippets
"""


@dataclass
class RAGAgent:
    """ReAct agent for codebase Q&A with MCP tool integration."""

    vector_store: IVectorStore
    mcp_client: MCPClientManager | None
    gemini_api_key: str
    codebase_id: str
    local_path: str
    model_name: str = "gemini-2.5-flash"

    def __post_init__(self) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.gemini_api_key,
            temperature=0.3,
        )
        self._tools = self._create_tools()
        self._agent = create_react_agent(
            self._llm,
            self._tools,
            state_modifier=AGENT_SYSTEM_PROMPT,
        )

    def _create_tools(self) -> list[Any]:
        """Create tools for the agent."""
        vector_store = self.vector_store
        codebase_id = self.codebase_id
        local_path = self.local_path

        @tool
        async def search_code(query: str, top_k: int = 5) -> str:
            """Search for code snippets semantically similar to the query.

            Args:
                query: Natural language description of what you're looking for
                top_k: Number of results to return (default: 5)

            Returns:
                Relevant code snippets with file paths and line numbers
            """
            results = await vector_store.search(codebase_id, query, top_k)

            if not results:
                return "No relevant code found."

            output = []
            for i, result in enumerate(results, 1):
                chunk = result.chunk
                output.append(
                    f"## Result {i} (score: {result.score:.3f})\n"
                    f"**File:** {chunk.file_path}\n"
                    f"**Lines:** {chunk.start_line}-{chunk.end_line}\n"
                    f"```\n{chunk.content}\n```"
                )

            return "\n\n".join(output)

        @tool
        async def read_file(file_path: str) -> str:
            """Read the contents of a specific file.

            Args:
                file_path: Path to the file relative to repository root

            Returns:
                File contents
            """
            from pathlib import Path

            try:
                full_path = Path(local_path) / file_path
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                return content
            except FileNotFoundError:
                return f"File not found: {file_path}"
            except Exception as e:
                return f"Error reading file: {e}"

        @tool
        async def list_files(directory: str = "", extension: str = "") -> str:
            """List files in the repository.

            Args:
                directory: Directory to list (empty for root)
                extension: Filter by extension (e.g., '.py')

            Returns:
                List of file paths
            """
            from pathlib import Path
            import json

            base_path = Path(local_path)
            search_path = base_path / directory if directory else base_path

            files = []
            for item in search_path.rglob("*"):
                if item.is_file():
                    if extension and not item.suffix == extension:
                        continue
                    rel_path = item.relative_to(base_path)
                    files.append(str(rel_path))

            return json.dumps(files[:50], indent=2)

        return [search_code, read_file, list_files]

    async def run(
        self,
        query: str,
        conversation_history: list[dict[str, Any]],
    ) -> tuple[str, list[str]]:
        """Run the agent and return (response, source_files)."""

        messages: list[BaseMessage] = []
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=query))

        result = await self._agent.ainvoke({"messages": messages})

        final_messages = result.get("messages", [])
        if final_messages:
            response = str(final_messages[-1].content)
        else:
            response = "I couldn't generate a response."

        source_files: list[str] = []
        for msg in final_messages:
            if hasattr(msg, "tool_calls"):
                for tool_call in msg.tool_calls:
                    if tool_call.get("name") == "read_file":
                        file_path = tool_call.get("args", {}).get("file_path")
                        if file_path and file_path not in source_files:
                            source_files.append(file_path)

        return response, source_files
