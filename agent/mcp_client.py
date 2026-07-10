"""Thin wrapper around mcp-server-datahub over stdio."""

import json
import subprocess
from typing import Any


class MCPClient:
    """Launches and communicates with mcp-server-datahub over stdio JSON-RPC."""

    def __init__(self, command: str = "uvx", args: list[str] | None = None):
        self._command = command
        self._args = args or ["mcp-server-datahub@latest"]
        self._process: subprocess.Popen | None = None

    def start(self) -> None:
        """Start the MCP server subprocess."""
        self._process = subprocess.Popen(
            [self._command, *self._args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON-RPC call to the MCP server and return the result."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP server not started. Call start() first.")
        line = json.dumps(payload) + "\n"
        self._process.stdin.write(line)
        self._process.stdin.flush()
        response_line = self._process.stdout.readline()
        if not response_line:
            _, stderr = self._process.communicate()
            raise RuntimeError(f"MCP server closed unexpectedly. stderr: {stderr}")
        result = json.loads(response_line)
        if "error" in result:
            raise RuntimeError(f"MCP error: {result['error']}")
        return result.get("result", {})

    def stop(self) -> None:
        """Terminate the MCP server subprocess."""
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=10)
            self._process = None
