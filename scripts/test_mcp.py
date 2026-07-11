"""Test MCP server with the official mcp Python client."""
import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(
        command="mcp-server-datahub",
        env={**os.environ, "DATAHUB_GMS_URL": "http://localhost:8080"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.initialize()
            print("Connected to:", result.serverInfo.name, result.serverInfo.version)

            tools = await session.list_tools()
            print(f"Tools available: {len(tools.tools)}")
            for t in tools.tools:
                desc = t.description[:80] if t.description else ""
                print(f"  - {t.name}: {desc}")

            # Try a search
            print("\nSearching for 'customers'...")
            search_result = await session.call_tool("search", {"query": "customers"})
            for content in search_result.content:
                if hasattr(content, "text"):
                    print(content.text[:500])

asyncio.run(main())
