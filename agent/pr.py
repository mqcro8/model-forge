"""Open a branch and PR via GitHub API."""

import os
import re
from pathlib import Path
from typing import Any

import requests


def _check_env(var: str) -> str:
    val = os.environ.get(var)
    if not val:
        raise EnvironmentError(f"{var} is required but not set")
    return val


def open_pr(
    repo: str,
    model_name: str,
    plan: dict[str, Any],
    files: dict[str, Path],
) -> str:
    """Open a branch, commit generated files, and create a PR.

    Args:
        repo: "owner/repo" GitHub repository identifier.
        model_name: Name of the generated model (used for branch name).
        plan: The build plan dict (for PR description).
        files: Dict mapping logical names to Paths (from render.render_model).

    Returns:
        URL of the created PR.
    """
    token = _check_env("GITHUB_TOKEN")
    branch = f"model-forge/{model_name}"

    # TODO: implement the full flow:
    # 1. Get default branch SHA from GitHub API
    # 2. Create a new branch from that SHA
    # 3. Create/update each file via the Contents API
    # 4. Open a PR with a description listing DataHub tables/columns used
    # 5. Return the PR URL

    raise NotImplementedError("PR automation not yet implemented")
