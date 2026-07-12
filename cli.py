#!/usr/bin/env python3
"""Model Forge — CLI entry point."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from agent.generator import generate_build_plan, GenerationError
from agent.mcp_client import MCPClient
from agent.render import render_model
from agent.pr import open_pr
from agent.writeback import annotate_source_tables


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
        help="Skip the dbt build step",
    )
    generate_parser.add_argument(
        "--skip-pr",
        action="store_true",
        help="Skip the PR creation step",
    )
    generate_parser.add_argument(
        "--skip-writeback",
        action="store_true",
        help="Skip the DataHub write-back step",
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

    print(json.dumps(plan, indent=2))

    output_dir = Path(args.output_dir)
    paths = render_model(plan, output_dir)

    print(f"\nGenerated model: {plan['model_name']}", file=sys.stderr)
    for key, path in paths.items():
        print(f"  {key}: {path}", file=sys.stderr)

    if not args.skip_dbt:
        _run_dbt_build(plan["model_name"], output_dir)

    if not args.skip_pr:
        _run_pr(plan, paths)

    if not args.skip_writeback:
        _run_writeback(plan)


def _run_dbt_build(model_name: str, output_dir: Path) -> None:
    """Copy generated files into the warehouse and run dbt build."""
    warehouse_models = Path("warehouse/models")
    target_dir = warehouse_models / "generated"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy the three generated files
    expected_suffixes = {".sql", ".yml"}
    for src in output_dir.iterdir():
        if src.is_file() and src.suffix in expected_suffixes:
            dest = target_dir / src.name
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  Copied {src.name} -> {dest}", file=sys.stderr)

    # Run dbt build for just this model
    result = subprocess.run(
        ["dbt", "build", "--select", model_name],
        cwd="warehouse",
        capture_output=True,
        text=True,
    )
    print(result.stdout, file=sys.stderr)
    if result.returncode != 0:
        print(f"dbt build failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"dbt build passed for {model_name}", file=sys.stderr)


def _run_pr(plan: dict[str, Any], paths: dict[str, Path]) -> None:
    """Create a GitHub PR with the generated files."""
    import os

    repo = os.environ.get("GITHUB_REPO")
    if not repo:
        print("GITHUB_REPO not set — skipping PR creation", file=sys.stderr)
        return

    try:
        pr_url = open_pr(repo, plan["model_name"], plan, paths)
        print(f"PR created: {pr_url}", file=sys.stderr)
    except EnvironmentError as exc:
        print(f"PR creation skipped: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"PR creation failed: {exc}", file=sys.stderr)


def _run_writeback(plan: dict[str, Any]) -> None:
    """Write metadata annotations back to DataHub."""
    import os
    gms_server = os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080")

    # Build source URNs from the plan
    source_urns = []
    for ref in plan.get("source_refs", []):
        urn = f"urn:li:dataset:(urn:li:dataPlatform:duckdb,model_forge.main.{ref['table_name']},PROD)"
        source_urns.append(urn)

    if not source_urns:
        print("No source URNs to annotate", file=sys.stderr)
        return

    target_name = plan["model_name"]
    target_urn = f"urn:li:dataset:(urn:li:dataPlatform:duckdb,model_forge.main.{target_name},PROD)"

    try:
        annotate_source_tables(
            gms_server=gms_server,
            source_urns=source_urns,
            model_name=target_name,
            model_description=plan.get("description", ""),
            target_urn=target_urn,
        )
        print("DataHub write-back complete", file=sys.stderr)
    except Exception as exc:
        print(f"Write-back failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
