"""
MCP Client Manager.

This module provides a client to connect to MCP servers and invoke their tools.
It can connect to:
- Our custom codebase server
- External MCP servers (filesystem, GitHub, etc.)

The client integrates with LangGraph to make MCP tools available to agents.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from src.application.interfaces.i_mcp_client import IMCPClient, MCPTool, MCPResource


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


class MCPClientManager(IMCPClient):
    """Manages connections to multiple MCP servers.

    This client can connect to various MCP servers and expose their tools
    to LangGraph agents. It handles:
    - Connection lifecycle management
    - Tool discovery and invocation
    - Resource access
    """

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._current_server: str | None = None

    @asynccontextmanager
    async def _connect_to_server(self, config: MCPServerConfig):
        """Context manager for server connection."""
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or None,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def connect(self, server_name: str) -> None:
        """Connect to an MCP server by name.

        Supported servers:
        - "filesystem": Access local file system
        - "github": Access GitHub repositories
        - "codebase": Our custom codebase server
        """
        configs = {
            "filesystem": MCPServerConfig(
                name="filesystem",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "./repos"],
            ),
            "github": MCPServerConfig(
                name="github",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_TOKEN": ""},
            ),
        }

        if server_name not in configs:
            raise ValueError(f"Unknown server: {server_name}")

        self._current_server = server_name

    async def disconnect(self) -> None:
        """Disconnect from current server."""
        if self._current_server and self._current_server in self._sessions:
            del self._sessions[self._current_server]
        self._current_server = None

    async def list_tools(self) -> list[MCPTool]:
        """List tools from the connected server."""
        if not self._current_server:
            return []

        config = self._get_config(self._current_server)

        async with self._connect_to_server(config) as session:
            result = await session.list_tools()
            return [
                MCPTool(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=tool.inputSchema,
                )
                for tool in result.tools
            ]

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        if not self._current_server:
            raise RuntimeError("Not connected to any server")

        config = self._get_config(self._current_server)

        async with self._connect_to_server(config) as session:
            result = await session.call_tool(tool_name, arguments)
            if result.content:
                return "\n".join(c.text for c in result.content if hasattr(c, "text"))
            return None

    async def list_resources(self) -> list[MCPResource]:
        """List resources from the connected server."""
        if not self._current_server:
            return []

        config = self._get_config(self._current_server)

        async with self._connect_to_server(config) as session:
            result = await session.list_resources()
            return [
                MCPResource(
                    uri=str(r.uri),
                    name=r.name,
                    mime_type=r.mimeType,
                )
                for r in result.resources
            ]

    async def read_resource(self, uri: str) -> str:
        """Read a resource from the server."""
        if not self._current_server:
            raise RuntimeError("Not connected to any server")

        config = self._get_config(self._current_server)

        async with self._connect_to_server(config) as session:
            result = await session.read_resource(uri)
            if result.contents:
                return "\n".join(c.text for c in result.contents if hasattr(c, "text"))
            return ""

    def _get_config(self, server_name: str) -> MCPServerConfig:
        """Get server configuration by name."""
        configs = {
            "filesystem": MCPServerConfig(
                name="filesystem",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "./repos"],
            ),
            "github": MCPServerConfig(
                name="github",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
            ),
        }
        return configs[server_name]


def get_mcp_tools_for_langgraph(client: MCPClientManager) -> list[dict]:
    """Convert MCP tools to LangGraph-compatible tool definitions.

    This function bridges MCP tools with LangGraph, allowing agents
    to use MCP server tools seamlessly.
    """

    async def _get_tools():
        tools = await client.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in tools
        ]

    return asyncio.get_event_loop().run_until_complete(_get_tools())
