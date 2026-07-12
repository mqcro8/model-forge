# Model Forge

An agent that generates dbt models grounded in real DataHub metadata. It reads schemas and lineage through the MCP Server, plans a model against that metadata, renders it deterministically, proves it works with `dbt build`, opens a GitHub PR, and writes annotations back to DataHub.

**Built for the "Build with DataHub" Hackathon** — Metadata-Aware Code Generation category.

---

## Quick start (under 5 minutes)

### Prerequisites

- **Python 3.11+**
- **Docker** (Docker Desktop, Podman Desktop, or Rancher Desktop)
- **DataHub CLI**: `pip install acryl-datahub`
- **uv** (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Anthropic API key** (`ANTHROPIC_API_KEY`)
- Optional: **GitHub token** (`GITHUB_TOKEN`) + repo (`GITHUB_REPO`) for PR creation

### Step 1 — Start DataHub

```bash
datahub docker quickstart
```

Takes ~2 minutes on first run. The UI will be at `http://localhost:9002`.

### Step 2 — Seed the warehouse and ingest metadata

```bash
cd warehouse
dbt seed
dbt run
dbt docs generate
cd ..
```

Then ingest into DataHub:

```bash
datahub ingest -c recipes/ingest.yml
```

This gives DataHub real schema metadata (customers, orders, order_items) from your local dbt project — not fake demo data.

### 3 — Connect the MCP server

```bash
uvx mcp-server-datahub@latest
```

The MCP server connects to DataHub's GMS API at `http://localhost:8080` by default.

### 4 — Generate a model

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python cli.py generate "build a customer LTV mart showing total spend per customer"
```

This runs the full pipeline:
1. Queries DataHub via MCP for real table schemas
2. Claude plans a build plan grounded in actual metadata
3. Renders `model.sql`, `schema.yml`, and a unit test
4. Runs `dbt build` against the local DuckDB warehouse
5. Optionally opens a GitHub PR and writes annotations back to DataHub

### 5 — Verify

```bash
cd warehouse
dbt build
```

All tests should pass, including the generated unit test.

---

## How it works

```
 ┌──────────┐     MCP      ┌──────────────┐
 │ DataHub  │◄────────────►│ MCP Server   │
 │ (schema, │  stdio/SSE   │ (tool defs)  │
 │ lineage) │              └──────┬───────┘
 └──────────┘                     │
                                  ▼
                         ┌────────────────┐
                         │  Generator     │
                         │  (Claude API)  │──► structured JSON plan
                         └────────────────┘
                                  │
                         ┌────────▼────────┐
                         │  Renderer       │
                         │  (Jinja2)       │──► model.sql + schema.yml + unit test
                         └────────┬────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  dbt build (DuckDB)        │──► proves the model works
                    └─────────────┬─────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                                       ▼
     ┌────────────────┐                     ┌────────────────┐
     │  GitHub PR     │                     │  DataHub       │
     │  (commit +     │                     │  write-back    │
     │   open PR)     │                     │  (annotations) │
     └────────────────┘                     └────────────────┘
```

**Key design decision:** the LLM never writes raw YAML. It emits a structured JSON build plan; `render.py` fills Jinja templates deterministically. This guarantees syntactically valid dbt config on every run.

---

## Project structure

```
model-forge/
├── README.md
├── LICENSE                     # Apache 2.0
├── cli.py                      # Entry point: python cli.py generate "<ask>"
├── requirements.txt
├── agent/
│   ├── mcp_client.py           # Official MCP SDK, talks to mcp-server-datahub
│   ├── generator.py            # Claude tool-use loop → structured build plan
│   ├── prompts.py              # System prompt, MCP tool defs, plan schema
│   ├── render.py               # Jinja2: plan → SQL + YAML
│   ├── writeback.py            # DataHub metadata annotation + lineage
│   └── pr.py                   # GitHub PR automation (branch, commit, open)
├── templates/
│   ├── model.sql.jinja         # dbt model SQL (CTEs, joins, filters)
│   ├── schema.yml.jinja        # dbt schema with data tests
│   └── unit_test.jinja         # dbt v1.8+ unit test YAML
├── warehouse/                  # Seed dbt-duckdb project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── seeds/                  # customers.csv, orders.csv, order_items.csv
│   └── models/staging/         # 3 staging models, 22 data tests
├── recipes/
│   └── ingest.yml              # DataHub dbt ingestion recipe
├── examples/                   # Sample output for judges
│   ├── prompt.txt
│   ├── customer_ltv_mart.sql
│   ├── customer_ltv_mart.yml
│   └── customer_ltv_mart_unit_test.yml
├── scripts/
│   ├── setup_datahub.sh        # One-command setup (DataHub + warehouse + ingest)
│   ├── run_demo.sh             # Demo run (skips PR + writeback)
│   ├── test_render.py          # Template rendering test
│   └── test_mcp.py             # MCP server connection test
└── .github/workflows/ci.yml    # CI: dbt build on every PR
```

---

## CLI options

```bash
# Generate with all steps
python cli.py generate "build a customer LTV mart"

# Skip PR creation (no GitHub token needed)
python cli.py generate "build a customer LTV mart" --skip-pr

# Skip DataHub write-back
python cli.py generate "build a customer LTV mart" --skip-writeback

# Skip dbt build
python cli.py generate "build a customer LTV mart" --skip-dbt

# Custom output directory
python cli.py generate "build a customer LTV mart" --output-dir ./my-output
```

---

## Running tests

```bash
# Test template rendering (no dependencies)
python -m scripts.test_render

# Test MCP server connection (requires DataHub running)
python -m scripts.test_mcp

# Run all dbt tests
cd warehouse && dbt build
```

---

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API access for generation |
| `GITHUB_TOKEN` | No | GitHub PAT for PR creation (repo scope) |
| `GITHUB_REPO` | No | Target repo, e.g. `owner/repo` |
| `DATAHUB_GMS_URL` | No | DataHub GMS endpoint (default: `http://localhost:8080`) |

---

## Architecture decisions

1. **Anthropic SDK directly** — not Claude Code headless mode. More portable, judges can run it, costs pennies per generation (~$0.01–0.05 per run on Haiku 4.5).
2. **Structured plan, not raw SQL** — LLM emits JSON matching a strict schema; Jinja templates handle all YAML. Eliminates LLM YAML hallucinations.
3. **DuckDB** — zero-config warehouse, fast for demos, dbt-duckdb adapter works out of the box.
4. **Fail-fast** — if DataHub is unreachable or MCP returns empty results, the agent throws immediately. No silent fallback to guessed column names.
5. **Official MCP SDK** — `mcp` Python package with asyncio sync bridge. Tested against real DataHub.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Demo

Run the demo locally:

```bash
bash scripts/run_demo.sh
```

This executes a generation run with `--skip-pr --skip-writeback` so it works without GitHub or DataHub write-back access.

For the full experience, run:

```bash
python cli.py generate "build a customer LTV mart showing total spend per customer"
```

This will: query DataHub → plan the model → render → dbt build → open PR → write back to DataHub.
