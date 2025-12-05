"""
MCP Server for File System Operations.

A simpler MCP server that provides direct file system access to a cloned repository.
This can be used as an alternative to the full codebase server when vector search
is not needed.

Usage:
    server = FileMCPServer("/path/to/repo")
    await server.run()
"""

import json
from pathlib import Path
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource
from pydantic import AnyUrl


class FileMCPServer:
    """Simple MCP Server for file system operations on a repository."""

    def __init__(self, repo_path: str, allowed_extensions: list[str] | None = None):
        self.repo_path = Path(repo_path)
        self.allowed_extensions = allowed_extensions or [
            ".py",
            ".js",
            ".ts",
            ".md",
            ".json",
            ".yaml",
            ".yml",
        ]

        self.server = Server("file-server")
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register MCP handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="read_file",
                    description="Read the contents of a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File path relative to repository root",
                            }
                        },
                        "required": ["path"],
                    },
                ),
                Tool(
                    name="list_directory",
                    description="List contents of a directory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path relative to repository root",
                                "default": ".",
                            }
                        },
                    },
                ),
                Tool(
                    name="search_files",
                    description="Search for files by name pattern",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern to search for (e.g., '*.py', 'test_*.py')",
                            }
                        },
                        "required": ["pattern"],
                    },
                ),
                Tool(
                    name="grep",
                    description="Search for a pattern in file contents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Text pattern to search for",
                            },
                            "file_pattern": {
                                "type": "string",
                                "description": "Glob pattern for files to search (default: all)",
                                "default": "*",
                            },
                        },
                        "required": ["pattern"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            if name == "read_file":
                return await self._read_file(arguments["path"])
            elif name == "list_directory":
                return await self._list_directory(arguments.get("path", "."))
            elif name == "search_files":
                return await self._search_files(arguments["pattern"])
            elif name == "grep":
                return await self._grep(
                    arguments["pattern"],
                    arguments.get("file_pattern", "*"),
                )
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List files as resources."""
            resources = []
            for ext in self.allowed_extensions:
                for file_path in self.repo_path.rglob(f"*{ext}"):
                    if not self._is_ignored(file_path):
                        rel_path = file_path.relative_to(self.repo_path)
                        resources.append(
                            Resource(
                                uri=AnyUrl(f"file://{rel_path}"),
                                name=str(rel_path),
                                mimeType="text/plain",
                            )
                        )
            return resources[:100]

        @self.server.read_resource()
        async def read_resource(uri: AnyUrl) -> str:
            uri_str = str(uri)
            path = uri_str.replace("file://", "")
            full_path = self.repo_path / path
            self._validate_path(full_path)
            return full_path.read_text(encoding="utf-8", errors="ignore")

    def _validate_path(self, path: Path) -> None:
        """Ensure path is within repo and doesn't contain traversal."""
        resolved = path.resolve()
        if not str(resolved).startswith(str(self.repo_path.resolve())):
            raise ValueError("Path traversal not allowed")

    def _is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored."""
        ignored = {".git", "node_modules", "__pycache__", ".venv", "venv"}
        return any(part in ignored for part in path.parts)

    async def _read_file(self, path: str) -> list[TextContent]:
        """Read a file."""
        try:
            full_path = self.repo_path / path
            self._validate_path(full_path)
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            return [TextContent(type="text", text=content)]
        except FileNotFoundError:
            return [TextContent(type="text", text=f"File not found: {path}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error reading file: {e}")]

    async def _list_directory(self, path: str) -> list[TextContent]:
        """List directory contents."""
        try:
            full_path = self.repo_path / path
            self._validate_path(full_path)

            if not full_path.is_dir():
                return [TextContent(type="text", text=f"Not a directory: {path}")]

            items = []
            for item in sorted(full_path.iterdir()):
                if not self._is_ignored(item):
                    rel_path = item.relative_to(self.repo_path)
                    item_type = "dir" if item.is_dir() else "file"
                    items.append({"name": str(rel_path), "type": item_type})

            return [TextContent(type="text", text=json.dumps(items, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async def _search_files(self, pattern: str) -> list[TextContent]:
        """Search for files matching a pattern."""
        matches = []
        for match in self.repo_path.rglob(pattern):
            if not self._is_ignored(match) and match.is_file():
                matches.append(str(match.relative_to(self.repo_path)))

        return [TextContent(type="text", text=json.dumps(matches[:50], indent=2))]

    async def _grep(self, pattern: str, file_pattern: str) -> list[TextContent]:
        """Search for pattern in files."""
        results = []

        for file_path in self.repo_path.rglob(file_pattern):
            if self._is_ignored(file_path) or not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if pattern.lower() in line.lower():
                        rel_path = file_path.relative_to(self.repo_path)
                        results.append(
                            {
                                "file": str(rel_path),
                                "line": i,
                                "content": line.strip()[:200],
                            }
                        )
            except Exception:
                continue

        return [TextContent(type="text", text=json.dumps(results[:50], indent=2))]

    async def run(self) -> None:
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
