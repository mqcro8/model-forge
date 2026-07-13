"""Thin wrapper around mcp-server-datahub using the official MCP Python SDK."""

import asyncio
import os
import sys
import time
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEFAULT_TIMEOUT = 30


class MCPError(Exception):
    """Raised when the MCP server is unreachable or returns an error."""


class MCPClient:
    """Launches and communicates with mcp-server-datahub over stdio."""

    def __init__(
        self,
        command: str = "mcp-server-datahub",
        datahub_server: str = "http://localhost:8080",
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._command = command
        self._datahub_server = datahub_server
        self._timeout = timeout
        self._session: ClientSession | None = None
        self._context_stack = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stderr_log: list[str] = []

    @property
    def stderr_log(self) -> list[str]:
        """Return collected stderr messages."""
        return list(self._stderr_log)

    def _log_stderr(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self._stderr_log.append(entry)
        print(entry, file=sys.stderr)

    def start(self) -> None:
        """Start the MCP server and perform initialization handshake."""
        self._loop = asyncio.new_event_loop()
        try:
            self._loop.run_until_complete(
                asyncio.wait_for(self._async_start(), timeout=self._timeout)
            )
        except asyncio.TimeoutError:
            self._log_stderr(f"MCP server startup timed out after {self._timeout}s")
            raise MCPError(
                f"MCP server failed to start within {self._timeout}s — "
                "is mcp-server-datahub installed and DataHub running?"
            ) from None
        except FileNotFoundError as exc:
            self._log_stderr(f"MCP server command not found: {self._command}")
            raise MCPError(
                f"MCP server command '{self._command}' not found — "
                "install it with: pip install mcp-server-datahub"
            ) from exc
        except Exception as exc:
            self._log_stderr(f"MCP server failed to start: {exc}")
            raise MCPError(f"MCP server failed to start: {exc}") from exc

    async def _async_start(self) -> None:
        env = {**os.environ, "DATAHUB_GMS_URL": self._datahub_server}
        params = StdioServerParameters(
            command=self._command,
            env=env,
        )
        self._context_stack = stdio_client(params)
        self._read, self._write = await self._context_stack.__aenter__()
        try:
            self._session = ClientSession(self._read, self._write)
            await self._session.__aenter__()
        except Exception:
            # If session init fails, clean up the transport we just opened
            await self._context_stack.__aexit__(None, None, None)
            self._context_stack = None
            raise
        self._log_stderr("MCP server initialized")
        await self._session.initialize()

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server."""
        try:
            return self._loop.run_until_complete(
                asyncio.wait_for(self._async_list_tools(), timeout=self._timeout)
            )
        except asyncio.TimeoutError:
            self._log_stderr(f"list_tools timed out after {self._timeout}s")
            raise MCPError(f"list_tools timed out after {self._timeout}s") from None

    async def _async_list_tools(self) -> list[dict[str, Any]]:
        if self._session is None:
            raise MCPError("MCP session not started — call start() first")
        result = await self._session.list_tools()
        tools = [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema if hasattr(t, "inputSchema") else {},
            }
            for t in result.tools
        ]
        self._log_stderr(f"Listed {len(tools)} MCP tools")
        return tools

    def run_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Call a tool on the MCP server and return the text result (sync)."""
        try:
            return self._loop.run_until_complete(
                asyncio.wait_for(self._async_call_tool(name, arguments), timeout=self._timeout)
            )
        except asyncio.TimeoutError:
            self._log_stderr(f"Tool '{name}' timed out after {self._timeout}s")
            raise MCPError(
                f"Tool '{name}' timed out after {self._timeout}s — "
                "DataHub may be unreachable or overloaded"
            ) from None

    async def _async_call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        if self._session is None:
            raise MCPError("MCP session not started — call start() first")
        result = await self._session.call_tool(name, arguments or {})
        parts = []
        for content in result.content:
            if hasattr(content, "text"):
                parts.append(content.text)
        text = "\n".join(parts)
        if not text.strip():
            self._log_stderr(f"Tool '{name}' returned empty result")
        return text

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
            except Exception as exc:
                self._log_stderr(f"Warning: MCP session teardown error: {exc}")
            self._session = None
        if self._context_stack:
            try:
                await self._context_stack.__aexit__(None, None, None)
            except Exception as exc:
                self._log_stderr(f"Warning: MCP transport teardown error: {exc}")
            self._context_stack = None
