#!/usr/bin/env python3
"""Model Forge — CLI entry point."""

import argparse
import json
import sys
from pathlib import Path

from agent.generator import generate_build_plan, GenerationError
from agent.mcp_client import MCPClient
from agent.render import render_model


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Model Forge: generate a dbt model grounded in DataHub metadata."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Generate a dbt model")
    generate_parser.add_argument("prompt", help="Natural-language description of the model to build")
    generate_parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to write generated files (default: ./output)",
    )
    generate_parser.add_argument(
        "--skip-dbt",
        action="store_true",
        help="Skip the dbt build step (for debugging)",
    )
    generate_parser.add_argument(
        "--skip-pr",
        action="store_true",
        help="Skip the PR creation step (for debugging)",
    )
    generate_parser.add_argument(
        "--skip-writeback",
        action="store_true",
        help="Skip the DataHub write-back step (for debugging)",
    )

    args = parser.parse_args()

    if args.command == "generate":
        _run_generate(args)


def _run_generate(args: argparse.Namespace) -> None:
    mcp = MCPClient()
    try:
        mcp.start()
        plan = generate_build_plan(args.prompt, mcp)
    except GenerationError as exc:
        print(f"Generation failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"MCP error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        mcp.stop()

    output_dir = Path(args.output_dir)
    paths = render_model(plan, output_dir)

    print(f"Generated model: {plan['model_name']}")
    for key, path in paths.items():
        print(f"  {key}: {path}")

    if not args.skip_dbt:
        print("dbt build step not yet implemented — use --skip-dbt for now")

    if not args.skip_pr:
        print("PR creation step not yet implemented — use --skip-pr for now")

    if not args.skip_writeback:
        print("Write-back step not yet implemented — use --skip-writeback for now")


if __name__ == "__main__":
    main()
