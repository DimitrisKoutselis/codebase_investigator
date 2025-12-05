from abc import ABC, abstractmethod
from typing import Any, List
from dataclasses import dataclass


@dataclass
class MCPTool:
    """Represents an MCP tool available from a server."""

    name: str
    description: str
    parameters: dict


@dataclass
class MCPResource:
    """Represents an MCP resource."""

    uri: str
    name: str
    mime_type: str | None = None


class IMCPClient(ABC):
    """Interface for MCP (Model Context Protocol) client operations.

    MCP allows LLMs to securely access external tools and data sources.
    This interface abstracts the MCP client so different implementations
    can be swapped (e.g., stdio, SSE, websocket transports).
    """

    @abstractmethod
    async def connect(self, server_name: str) -> None:
        """Connect to an MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        pass

    @abstractmethod
    async def list_tools(self) -> List[MCPTool]:
        """List available tools from the connected server."""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        pass

    @abstractmethod
    async def list_resources(self) -> List[MCPResource]:
        """List available resources from the connected server."""
        pass

    @abstractmethod
    async def read_resource(self, uri: str) -> str:
        """Read content from a resource URI."""
        pass
