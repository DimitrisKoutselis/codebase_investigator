"""
MCP Server for Codebase Operations.

This server exposes tools for searching and analyzing code in indexed repositories.
It can be used by LLMs to:
- Search code using semantic similarity
- Get file contents
- List repository structure
- Get code summaries

Usage:
    Run as standalone server:
        python -m src.infrastructure.mcp.servers.codebase_server

    Or import and integrate with your application:
        server = CodebaseMCPServer(vector_store, git_service)
        await server.run()
"""

import json
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource
from pydantic import AnyUrl

from src.application.interfaces.i_vector_store import IVectorStore
from src.application.interfaces.i_git_service import IGitService


class CodebaseMCPServer:
    """MCP Server exposing codebase search and analysis tools."""

    def __init__(
        self,
        vector_store: IVectorStore,
        git_service: IGitService,
        codebase_id: str,
        local_path: str,
    ):
        self.vector_store = vector_store
        self.git_service = git_service
        self.codebase_id = codebase_id
        self.local_path = local_path

        self.server = Server("codebase-investigator")
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register MCP tool and resource handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="search_code",
                    description="Search for code snippets semantically similar to the query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query to search for",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default: 5)",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="read_file",
                    description="Read the contents of a specific file in the repository",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file relative to repository root",
                            },
                        },
                        "required": ["file_path"],
                    },
                ),
                Tool(
                    name="list_files",
                    description="List all files in the repository or a specific directory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "Directory path (empty for root)",
                                "default": "",
                            },
                            "extensions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by file extensions (e.g., ['.py', '.js'])",
                            },
                        },
                    },
                ),
                Tool(
                    name="get_repo_summary",
                    description="Get a high-level summary of the repository structure",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            if name == "search_code":
                return await self._search_code(
                    arguments["query"],
                    arguments.get("top_k", 5),
                )
            elif name == "read_file":
                return await self._read_file(arguments["file_path"])
            elif name == "list_files":
                return await self._list_files(
                    arguments.get("directory", ""),
                    arguments.get("extensions"),
                )
            elif name == "get_repo_summary":
                return await self._get_repo_summary()
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available resources (files) in the codebase."""
            files = await self.git_service.list_files(self.local_path)
            return [
                Resource(
                    uri=AnyUrl(f"file://{self.codebase_id}/{f}"),
                    name=f,
                    mimeType=self._get_mime_type(f),
                )
                for f in files[:100]  # Limit to first 100
            ]

        @self.server.read_resource()
        async def read_resource(uri: AnyUrl) -> str:
            """Read a resource by URI."""
            # Parse URI: file://{codebase_id}/{file_path}
            uri_str = str(uri)
            parts = uri_str.replace("file://", "").split("/", 1)
            if len(parts) == 2 and parts[0] == self.codebase_id:
                content = await self.git_service.read_file(self.local_path, parts[1])
                return content
            raise ValueError(f"Invalid resource URI: {uri}")

    async def _search_code(self, query: str, top_k: int) -> list[TextContent]:
        """Search for code using vector similarity."""
        results = await self.vector_store.search(self.codebase_id, query, top_k)

        output = []
        for i, result in enumerate(results, 1):
            output.append(
                f"## Result {i} (score: {result.score:.3f})\n"
                f"**File:** {result.chunk.file_path}\n"
                f"**Lines:** {result.chunk.start_line}-{result.chunk.end_line}\n"
                f"```\n{result.chunk.content}\n```\n"
            )

        return [TextContent(type="text", text="\n".join(output) or "No results found")]

    async def _read_file(self, file_path: str) -> list[TextContent]:
        """Read a file's contents."""
        try:
            content = await self.git_service.read_file(self.local_path, file_path)
            return [TextContent(type="text", text=content)]
        except FileNotFoundError:
            return [TextContent(type="text", text=f"File not found: {file_path}")]

    async def _list_files(
        self,
        directory: str,
        extensions: list[str] | None,
    ) -> list[TextContent]:
        """List files in the repository."""
        files = await self.git_service.list_files(self.local_path, extensions)

        if directory:
            files = [f for f in files if f.startswith(directory)]

        return [TextContent(type="text", text=json.dumps(files, indent=2))]

    async def _get_repo_summary(self) -> list[TextContent]:
        """Get repository summary."""
        files = await self.git_service.list_files(self.local_path)

        # Count by extension
        extensions: dict[str, int] = {}
        for f in files:
            ext = f.rsplit(".", 1)[-1] if "." in f else "no_extension"
            extensions[ext] = extensions.get(ext, 0) + 1

        # Count by top-level directory
        directories: dict[str, int] = {}
        for f in files:
            parts = f.split("/")
            top_dir = parts[0] if len(parts) > 1 else "(root)"
            directories[top_dir] = directories.get(top_dir, 0) + 1

        summary = {
            "total_files": len(files),
            "files_by_extension": dict(sorted(extensions.items(), key=lambda x: -x[1])),
            "files_by_directory": dict(
                sorted(directories.items(), key=lambda x: -x[1])
            ),
        }

        return [TextContent(type="text", text=json.dumps(summary, indent=2))]

    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type for a file."""
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        mime_types = {
            "py": "text/x-python",
            "js": "text/javascript",
            "ts": "text/typescript",
            "json": "application/json",
            "md": "text/markdown",
            "yaml": "text/yaml",
            "yml": "text/yaml",
        }
        return mime_types.get(ext, "text/plain")

    async def run(self) -> None:
        """Run the MCP server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
