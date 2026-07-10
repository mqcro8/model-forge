# Handoff — What's Left to Build

**Date:** July 9, 2026
**Deadline:** August 10, 2026 (4.5 weeks)

---

## Current State

The full directory skeleton is in place with stubs for every file. Nothing has been run or tested yet. Below is the build order matching the PLAN.md timeline.

---

## Week 1 (Jul 9-15): DataHub infra + seed warehouse

### 1.1 [P0] Create a DataHub ingestion recipe
Missing file: `recipes/ingest.yml` (or similar). The recipe must point a `dbt` source at `warehouse/target/manifest.json` and `warehouse/target/catalog.json` after running `dbt docs generate`.

### 1.2 [P0] Write staging dbt models
`warehouse/models/staging/` is empty. Need:
- `stg_customers.sql` — select + rename from seed
- `stg_orders.sql` — select + rename from seed
- `stg_order_items.sql` — select + rename from seed
- `staging_schema.yml` — column-level tests and descriptions

This is the **actual schema** that DataHub will ingest and the agent will query.

### 1.3 [P0] Verify MCP client works
- Run `datahub docker quickstart` locally
- Run `uvx mcp-server-datahub@latest` and confirm `search`, `list_schema_fields`, `get_lineage` return real data
- Update `mcp_client.py` if JSON-RPC format differs from the stub

### 1.4 [P1] dbt setup + seed
- Run `cd warehouse && pip install dbt-duckdb && dbt seed && dbt run && dbt docs generate`
- Confirm `warehouse/target/manifest.json` and `catalog.json` exist
- Verify DuckDB file is created

---

## Week 2 (Jul 16-22): Generator loop + templates

### 2.1 [P0] Implement the full tool-call loop in `generator.py`
The current stub makes one API call but doesn't handle tool-use responses. Need:
- Parse `tool_use` content blocks from Claude
- Call the real MCP client methods (`search_datasets`, `get_dataset_schema`, `get_lineage`)
- Feed results back to Claude as `tool_result` blocks
- Loop until Claude emits the final JSON plan
- Handle max_tokens / retries / error recovery

### 2.2 [P0] Fix templates — they've never been rendered
All three Jinja templates need:
- Render test: feed a mock `plan` dict through `render.py` and inspect output
- Fix Jinja syntax issues (the SQL template has several bugs — leftover commas, clunky group_by, missing distinct handling)
- The `schema.yml.jinja` needs to handle the `tests:` array property correctly per dbt spec
- The unit test template uses an old dbt unit test format — verify against dbt v1.8+ `data_unit_test` syntax

### 2.3 [P0] End-to-end smoke test
Run `python cli.py generate "customer LTV mart" --skip-dbt --skip-pr --skip-writeback`
- Must connect to live DataHub
- Must call MCP tools
- Must emit valid JSON plan
- Must render three files to `output/`

### 2.4 [P1] `dbt build` integration in cli.py
After rendering, the CLI should shell out to `dbt build --select <model_name>` and check exit code.

---

## Week 3 (Jul 23-29): Write-back, PR, CI, hardening

### 3.1 [P0] Implement `writeback.py`
Replace `NotImplementedError` with real DataHub SDK calls:
- Emit `MetadataChangeProposal` to add descriptions on source datasets
- Call `add_lineage()` to show the new mart downstream of its sources
- Toggle `TOOLS_IS_MUTATION_ENABLED=true` only for this step

### 3.2 [P0] Implement `pr.py`
Replace `NotImplementedError` with GitHub API flow:
- `GET /repos/{repo}/git/ref/heads/main` to get base SHA
- `POST /repos/{repo}/git/refs` to create branch
- `PUT /repos/{repo}/contents/{path}` for each file
- `POST /repos/{repo}/pulls` to create PR
- PR body should list DataHub tables/columns used in generation

### 3.3 [P1] Fail-fast hardening
- `generator.py`: if MCP server is unreachable → `GenerationError`, not silent fallback
- `generator.py`: if DataHub returns no results for a query → `GenerationError`
- `mcp_client.py`: add timeouts and stderr collection
- All network calls should have configurable timeouts

### 3.4 [P1] CI workflow
- `.github/workflows/ci.yml` exists but needs testing
- Add a step that installs Python deps from `requirements.txt`
- Verify `dbt build` runs in CI (no DataHub dependency in CI)

### 3.5 [P2] Examples folder
- Replace placeholder files with actual generated output from a real run
- Add `writeback_screenshot.png`

---

## Week 4 (Jul 30-Aug 5): Polish + submission

### 4.1 [P0] README
Replace skeleton with full setup docs:
- Prerequisites (Docker, Python, dbt, DataHub CLI, uv)
- Step-by-step quick start (numbered)
- How judges run it in <5 minutes
- Architecture diagram or explanation
- Link to demo video

### 4.2 [P0] LICENSE
Replace placeholder with the actual Apache 2.0 full text.

### 4.3 [P1] Demo video (≤3 min)
Must show:
1. `datahub docker quickstart` starting
2. Warehouse seed + DataHub ingest
3. `python cli.py generate "..."` running end-to-end
4. `dbt build` passing
5. PR created
6. DataHub showing new annotations

### 4.4 [P2] Clean-clone test
Test from a completely fresh environment — the judge's machine.

### 4.5 [P2] Bonus: OSS contribution
A small PR to `datahub-skills` or `mcp-server-datahub` — even a docs fix.

---

## Open Questions

- **API vs Claude Code**: PLAN.md §7 leaves this open. The current skeleton assumes Anthropic API (`anthropic` Python SDK). If switching to headless Claude Code, the `generator.py` architecture changes significantly.
- **LTV definition**: Need to pin down the exact SQL logic for the demo model (e.g. total spend last 12 months, exclude cancelled orders?, include pending?).
- **dbt unit test format**: Need to verify which format dbt-duckdb supports (v1.8 `data_unit_test` or the newer `unit_test`).

---

## Files Summary

| File | Status | Notes |
|---|---|---|
| `agent/__init__.py` | ✅ Done | Empty |
| `agent/mcp_client.py` | ✅ Stub | Needs real-world testing |
| `agent/generator.py` | ⚠️ Partial | No tool-call loop yet |
| `agent/prompts.py` | ✅ Stub | Prompts defined, may need tuning |
| `agent/render.py` | ✅ Stub | Logic looks right, untested |
| `agent/writeback.py` | ⚠️ Stub | NotImplementedError |
| `agent/pr.py` | ⚠️ Stub | NotImplementedError |
| `templates/model.sql.jinja` | ⚠️ Draft | Needs fixing + testing |
| `templates/schema.yml.jinja` | ⚠️ Draft | Needs fixing + testing |
| `templates/unit_test.jinja` | ⚠️ Draft | Needs fixing + testing |
| `warehouse/dbt_project.yml` | ✅ Done | |
| `warehouse/profiles.yml` | ✅ Done | |
| `warehouse/seeds/*.csv` | ✅ Done | Sample data |
| `warehouse/models/staging/` | ❌ Empty | Need staging models |
| `cli.py` | ✅ Stub | Skips unimplemented steps |
| `.github/workflows/ci.yml` | ✅ Stub | Needs testing |
| `README.md` | ⚠️ Skeleton | Needs full docs |
| `LICENSE` | ⚠️ Placeholder | Needs full Apache 2.0 text |
| `requirements.txt` | ✅ Done | |
| `scripts/setup_datahub.sh` | ✅ Stub | |
| `scripts/run_demo.sh` | ✅ Stub | |
| `examples/*` | ⚠️ Placeholder | Needs real output |
| `.gitignore` | ✅ Done | |
| `handoff.md` | ✅ This file | |
