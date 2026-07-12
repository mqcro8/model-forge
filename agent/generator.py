"""Claude tool-use loop that produces a structured dbt build plan."""

import json
import os
import sys
from typing import Any

from anthropic import Anthropic, APIError, APITimeoutError, APIConnectionError

from .mcp_client import MCPClient, MCPError
from .prompts import BUILD_PLAN_SCHEMA, MCP_TOOL_DEFINITIONS, SYSTEM_PROMPT, make_user_prompt


class GenerationError(Exception):
    """Raised when generation fails (DataHub unreachable, table not found, etc.)."""


def _call_mcp_tool(mcp_client: MCPClient, tool_name: str, arguments: dict[str, Any]) -> str:
    """Call an MCP tool and return the text result.

    Raises GenerationError if the MCP call fails — no silent fallback.
    """
    try:
        result = mcp_client.run_tool(tool_name, arguments)
    except MCPError as exc:
        raise GenerationError(f"MCP tool '{tool_name}' failed: {exc}") from exc
    except Exception as exc:
        raise GenerationError(
            f"Unexpected error calling MCP tool '{tool_name}': {exc}"
        ) from exc

    if not result.strip():
        raise GenerationError(
            f"MCP tool '{tool_name}' returned empty result — "
            "is DataHub reachable and does it contain the expected data?"
        )
    return result


def _validate_plan(plan: dict[str, Any]) -> None:
    """Validate the plan has required top-level keys."""
    required = ["model_name", "description", "source_refs", "dimensions", "measures"]
    missing = [k for k in required if k not in plan]
    if missing:
        raise GenerationError(f"Generated plan is missing required keys: {missing}")

    if not plan["source_refs"]:
        raise GenerationError("Plan has no source_refs — the LLM found no tables in DataHub")
    if not plan["dimensions"] and not plan["measures"]:
        raise GenerationError("Plan has no dimensions or measures — nothing to build")


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

    try:
        client = Anthropic(api_key=api_key)
    except Exception as exc:
        raise GenerationError(f"Failed to initialize Anthropic client: {exc}") from exc

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": make_user_prompt(ask)},
    ]

    system = SYSTEM_PROMPT + "\n\nBuildPlan JSON schema:\n" + BUILD_PLAN_SCHEMA

    max_iterations = 15
    for iteration in range(max_iterations):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system=system,
                messages=messages,
                tools=MCP_TOOL_DEFINITIONS,
            )
        except APITimeoutError as exc:
            raise GenerationError(
                f"Anthropic API request timed out — check your network connection"
            ) from exc
        except APIConnectionError as exc:
            raise GenerationError(
                f"Cannot connect to Anthropic API — check your network and API key"
            ) from exc
        except APIError as exc:
            raise GenerationError(f"Anthropic API error: {exc}") from exc

        # Collect tool_use blocks and any text blocks
        tool_calls = []
        text_parts = []

        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(block)
            elif block.type == "text":
                text_parts.append(block.text)

        # If no tool calls, we're done — parse the text as the JSON plan
        if not tool_calls:
            combined_text = "\n".join(text_parts).strip()
            # Strip markdown fences if present
            if combined_text.startswith("```"):
                lines = combined_text.split("\n")
                lines = lines[1:]  # Remove opening fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                combined_text = "\n".join(lines)
            try:
                plan = json.loads(combined_text)
            except json.JSONDecodeError as exc:
                raise GenerationError(
                    f"Failed to parse LLM output as JSON: {exc}\n"
                    f"Output was:\n{combined_text}"
                ) from exc

            _validate_plan(plan)
            print(
                f"Generation complete: {len(tool_calls + [None])} tool calls "
                f"(iteration {iteration + 1}/{max_iterations})",
                file=sys.stderr,
            )
            return plan

        # Append assistant message (with tool_use blocks)
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool call and build tool_result blocks
        tool_results = []
        for block in tool_calls:
            result_text = _call_mcp_tool(mcp_client, block.name, block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                }
            )

        messages.append({"role": "user", "content": tool_results})

    raise GenerationError(
        f"Generation loop exceeded {max_iterations} iterations without producing a plan"
    )
