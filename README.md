# Model Forge

An agent that generates dbt models grounded in real DataHub metadata.

## Quick start

1. Start DataHub: `datahub docker quickstart`
2. Seed the warehouse: `cd warehouse && dbt seed && dbt run`
3. Ingest into DataHub: configure a dbt ingestion recipe pointing at `warehouse/target/`
4. Generate: `python cli.py generate "build a customer LTV mart"`

## Requirements

- Python 3.11+
- DataHub Core (self-hosted via `datahub docker quickstart`)
- dbt-core + dbt-duckdb
- Anthropic API key (`ANTHROPIC_API_KEY`)
- GitHub token with repo scope (`GITHUB_TOKEN`)
- GitHub repo identifier (`GITHUB_REPO`, e.g. `owner/repo` — only needed for PR creation)

## Project structure

```
agent/          — MCP client, generator, renderer, write-back, PR automation
templates/      — Jinja templates for dbt model, schema, unit tests
warehouse/      — Seed dbt-duckdb project (customers, orders, order_items)
scripts/        — Setup and demo scripts
examples/       — Sample prompts and outputs
cli.py          — Entry point
```

## How it works

1. Reads schema and lineage from a self-hosted DataHub instance via MCP
2. Claude generates a structured JSON build plan grounded in real metadata
3. Deterministic rendering produces model.sql, schema.yml, and a unit test
4. Runs `dbt build` against a local DuckDB warehouse
5. Opens a GitHub PR with the generated model
6. Writes annotations back to DataHub source tables

## License

Apache 2.0
