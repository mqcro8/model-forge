"""Deterministic rendering: build plan -> model.sql + schema.yml + unit test."""

import json
from pathlib import Path
from typing import Any

import jinja2

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _load_template(name: str) -> jinja2.Template:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=jinja2.StrictUndefined,
    )
    return env.get_template(name)


def render_model(plan: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    """Render all three output files from a build plan.

    Args:
        plan: A build plan dict conforming to BUILD_PLAN_SCHEMA.
        output_dir: Directory to write the generated files into.

    Returns:
        Dict mapping logical names to written file paths:
        {"model": Path, "schema": Path, "unit_test": Path}
    """
    model_name = plan["model_name"]
    output_dir.mkdir(parents=True, exist_ok=True)

    model_sql = _load_template("model.sql.jinja").render(plan=plan)
    schema_yml = _load_template("schema.yml.jinja").render(plan=plan)
    unit_test_sql = _load_template("unit_test.jinja").render(plan=plan)

    paths = {
        "model": output_dir / f"{model_name}.sql",
        "schema": output_dir / f"{model_name}.yml",
        "unit_test": output_dir / f"{model_name}_unit_test.sql",
    }

    paths["model"].write_text(model_sql, encoding="utf-8")
    paths["schema"].write_text(schema_yml, encoding="utf-8")
    paths["unit_test"].write_text(unit_test_sql, encoding="utf-8")

    return paths
