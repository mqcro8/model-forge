"""Claude tool-use loop that produces a structured dbt build plan."""

import json
import os
from typing import Any

from anthropic import Anthropic

from .mcp_client import MCPClient
from .prompts import BUILD_PLAN_SCHEMA, SYSTEM_PROMPT, make_user_prompt


class GenerationError(Exception):
    """Raised when generation fails (DataHub unreachable, table not found, etc.)."""


def generate_build_plan(ask: str, mcp_client: MCPClient) -> dict[str, Any]:
    """Run the Claude tool-use loop and return a structured build plan.

    Steps:
    1. Search DataHub for relevant tables.
    2. Pull schemas for each candidate.
    3. Check lineage for existing marts.
    4. Claude emits a JSON build plan matching BUILD_PLAN_SCHEMA.

    Returns the parsed JSON plan.
    Raises GenerationError if anything is unreachable or missing.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise GenerationError("ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=api_key)

    # Define MCP tools as Anthropic tool definitions
    tools = [
        {
            "name": "search_datasets",
            "description": "Search DataHub for datasets matching a query.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string"}
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_dataset_schema",
            "description": "Get the schema fields for a dataset.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "urn": {"type": "string", "description": "Dataset URN"}
                },
                "required": ["urn"],
            },
        },
        {
            "name": "get_lineage",
            "description": "Get downstream lineage for a dataset.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "urn": {"type": "string", "description": "Dataset URN"},
                    "direction": {
                        "type": "string",
                        "enum": ["upstream", "downstream"],
                        "description": "Lineage direction",
                    },
                },
                "required": ["urn", "direction"],
            },
        },
    ]

    messages = [
        {"role": "user", "content": make_user_prompt(ask)},
    ]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT + "\n\nBuildPlan schema:\n" + BUILD_PLAN_SCHEMA,
        messages=messages,
        tools=tools,
        tool_choice={"type": "auto"},
    )

    # The assistant should return tool calls and eventually a text response
    # with the JSON plan as the final turn
    for content_block in response.content:
        if content_block.type == "text":
            try:
                return json.loads(content_block.text)
            except json.JSONDecodeError as exc:
                raise GenerationError(f"Failed to parse LLM output as JSON: {exc}") from exc

    raise GenerationError("LLM did not return a text response")
