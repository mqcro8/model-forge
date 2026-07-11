"""Thin wrapper around mcp-server-datahub using the official MCP Python SDK."""

import asyncio
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Launches and communicates with mcp-server-datahub over stdio."""

    def __init__(
        self,
        command: str = "mcp-server-datahub",
        datahub_server: str = "http://localhost:8080",
    ):
        self._command = command
        self._datahub_server = datahub_server
        self._session: ClientSession | None = None
        self._context_stack = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        """Start the MCP server and perform initialization handshake."""
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._async_start())

    async def _async_start(self) -> None:
        env = {**os.environ, "DATAHUB_GMS_URL": self._datahub_server}
        params = StdioServerParameters(
            command=self._command,
            env=env,
        )
        self._context_stack = stdio_client(params)
        self._read, self._write = await self._context_stack.__aenter__()
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        await self._session.initialize()

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server."""
        return self._loop.run_until_complete(self._async_list_tools())

    async def _async_list_tools(self) -> list[dict[str, Any]]:
        result = await self._session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema if hasattr(t, "inputSchema") else {},
            }
            for t in result.tools
        ]

    def run_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Call a tool on the MCP server and return the text result (sync)."""
        return self._loop.run_until_complete(self._async_call_tool(name, arguments))

    async def _async_call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        result = await self._session.call_tool(name, arguments or {})
        parts = []
        for content in result.content:
            if hasattr(content, "text"):
                parts.append(content.text)
        return "\n".join(parts)

    def stop(self) -> None:
        """Terminate the MCP server subprocess."""
        if self._loop and self._loop.is_running():
            self._loop.run_until_complete(self._async_stop())
        if self._loop:
            self._loop.close()
            self._loop = None

    async def _async_stop(self) -> None:
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
        if self._context_stack:
            try:
                await self._context_stack.__aexit__(None, None, None)
            except Exception:
                pass
            self._context_stack = None
