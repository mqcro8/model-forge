# Handoff — What's Left to Build

**Date:** July 11, 2026
**Deadline:** August 10, 2026 (4 weeks remaining)

---

## Current State

Weeks 1-2 (DataHub infra + generator/templates) are **complete**. Week 3 is mostly done — writeback (3.1), PR automation (3.2), and CI workflow (3.4) are implemented. Remaining Week 3 work: fail-fast hardening (3.3), examples folder (3.5).

### What's Working
- DataHub running at `localhost:9002`, 92 events ingested (6 datasets, 22 assertions, lineage)
- MCP server verified — 8 tools, real metadata queries return results
- `agent/mcp_client.py` — official MCP SDK with sync bridge via asyncio
- `agent/generator.py` — real Claude tool-call loop (15 iterations), handles `tool_use`/`tool_result` blocks
- `agent/prompts.py` — MCP tool defs matching actual server, `BUILD_PLAN_SCHEMA` with `expect_rows`
- `agent/render.py` — Jinja2 env with `do` extension, renders model SQL, schema YAML, and unit test YAML
- `agent/pr.py` — full GitHub PR flow (branch, commit, open PR with description)
- `agent/writeback.py` — DataHub metadata annotation + lineage writeback via MCP
- All 3 Jinja templates produce valid dbt artifacts
- `dbt build` passes 35/35 (3 seeds, 22 data tests, 1 unit test, 4 view models)
- `cli.py` — full generate flow (MCP → plan → render → copy → dbt build → PR → writeback)

### Key DuckDB Quirks Discovered
- Inside CTEs, don't prefix columns with the CTE alias (e.g., use `customer_id` not `c.customer_id`)
- The final SELECT must use CTE output column names (aliases), not source column names
- Join key columns must be explicitly included in each CTE even if they're not dimensions/measures
- CTEs must be comma-separated: `c as (...), o as (...)`
- dbt unit tests use `expect:` (not `expected:`), bare `ref()` strings, `expect_rows` in schema

---

## Testing — What's Verified and What Requires External Dependencies

### Already Verified This Session (no external deps needed)

| Test | Command | Result |
|---|---|---|
| Full `dbt build` | `dbt build` in `warehouse/` | 35/35 PASS |
| Template rendering | `python scripts/test_render.py` | 3 files rendered correctly |
| MCP server connection | `python scripts/test_mcp.py` | Connects, lists 8 tools, searches customers |
| Writeback to DataHub | Direct Python call to `annotate_source_tables()` | Emitted successfully (descriptions + lineage) |
| All imports | `python -c "from agent.pr import open_pr"` etc. | No import errors |

### Can Be Tested But Requires External Credentials

| Test | Command | Requires |
|---|---|---|
| **Full CLI end-to-end** | `python cli.py generate "customer LTV mart" --skip-pr --skip-writeback` | `ANTHROPIC_API_KEY` env var |
| **CLI with writeback** | `python cli.py generate "..." --skip-pr` | `ANTHROPIC_API_KEY` + DataHub running |
| **CLI with PR** | `python cli.py generate "..." --skip-writeback` | `ANTHROPIC_API_KEY` + `GITHUB_TOKEN` + `GITHUB_REPO` |
| **Full pipeline** | `python cli.py generate "customer LTV mart"` | All three env vars + DataHub + GitHub |

### Cannot Be Tested Without Claude API

The **generator loop** (`agent/generator.py`) — the core agent logic that queries DataHub via MCP, calls Claude to plan, and returns a build plan — has never been run against a live Claude API. It's been structurally verified (mock plan renders correctly) but the actual tool-call loop is untested end-to-end.

### Available Test Scripts

| Script | What It Tests | Dependencies |
|---|---|---|
| `scripts/test_render.py` | Template rendering with mock plan | None (self-contained) |
| `scripts/test_mcp.py` | MCP server connection | DataHub running |
| `scripts/test_week1.sh` | Week 1 validation (DataHub + MCP + dbt) | DataHub running, Bash |

### Summary

The **rendering pipeline** and **dbt integration** are solid and verified. The **generator loop** (the brain) and **PR automation** are implemented but untested against real services. The **writeback** works against the live DataHub instance. The biggest gap is that the full `cli.py generate` flow has never been run with a real Claude API call — that's the critical end-to-end test before submission.

---

## Week 3 (Jul 23-29): Write-back, PR, CI, hardening

### 3.1 [P0] Implement `writeback.py` ✅ DONE
Implemented and tested against live DataHub:
- Emits `MetadataChangeProposal` to annotate source datasets with model reference
- Adds lineage via `make_lineage_mce` (sources → downstream model)
- Uses `SystemMetadataClass` properly (not raw dict)
- Verified: annotations and lineage accepted by DataHub GMS at port 8080

### 3.2 [P0] Implement `pr.py` ✅ DONE
Full GitHub PR flow implemented:
- Gets default branch, creates feature branch from HEAD
- Commits each generated file via Contents API (handles create + update)
- Opens PR with description listing DataHub sources, dimensions, measures
- Gracefully skips if `GITHUB_TOKEN` or `GITHUB_REPO` not set
- Needs real GitHub repo + token to verify end-to-end

### 3.3 [P1] Fail-fast hardening — PENDING
- `generator.py`: if MCP server is unreachable → `GenerationError`, not silent fallback
- `generator.py`: if DataHub returns no results for a query → `GenerationError`
- `mcp_client.py`: add timeouts and stderr collection
- All network calls should have configurable timeouts

### 3.4 [P1] CI workflow ✅ DONE
- `.github/workflows/ci.yml` triggers on `warehouse/**`, `templates/**`, `agent/**`, `cli.py`, `requirements.txt`
- Installs Python deps from `requirements.txt` + `dbt-duckdb`
- Runs `dbt build` in CI (no DataHub dependency in CI)

### 3.5 [P2] Examples folder — PENDING
- Replace placeholder files with actual generated output from a real run

---

## Week 4 (Jul 30-Aug 5): Polish + submission

### 4.1 [P0] README
Replace skeleton with full setup docs:
- Prerequisites (Docker, Python, dbt, DataHub CLI, uv)
- Step-by-step quick start (numbered)
- How judges run it in <5 minutes
- Architecture diagram or explanation
- Link to demo video

### 4.2 [P0] LICENSE ✅ DONE
Replaced placeholder with the actual Apache 2.0 full text.

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

## Files Summary

| File | Status | Notes |
|---|---|---|
| `agent/__init__.py` | ✅ Done | Empty |
| `agent/mcp_client.py` | ✅ Done | Official MCP SDK with sync bridge |
| `agent/generator.py` | ✅ Done | Real tool-call loop with Claude |
| `agent/prompts.py` | ✅ Done | MCP tool defs, BUILD_PLAN_SCHEMA |
| `agent/render.py` | ✅ Done | Jinja2 env with do extension |
| `agent/writeback.py` | ✅ Done | DataHub MCP + lineage writeback |
| `agent/pr.py` | ✅ Done | GitHub PR automation |
| `templates/model.sql.jinja` | ✅ Done | CTEs with join keys, comma-separated |
| `templates/schema.yml.jinja` | ✅ Done | Column-level data_tests |
| `templates/unit_test.jinja` | ✅ Done | expect:, bare ref() |
| `warehouse/dbt_project.yml` | ✅ Done | |
| `warehouse/profiles.yml` | ✅ Done | |
| `warehouse/seeds/*.csv` | ✅ Done | Sample data |
| `warehouse/models/staging/` | ✅ Done | 3 models, 22 tests |
| `warehouse/models/generated/` | ✅ Done | Test copies |
| `cli.py` | ✅ Done | Full generate flow |
| `.github/workflows/ci.yml` | ✅ Done | CI with agent/template path triggers |
| `README.md` | ⚠️ Skeleton | Needs full docs — Week 4 |
| `LICENSE` | ✅ Done | Apache 2.0 full text |
| `requirements.txt` | ✅ Done | anthropic, jinja2, requests, datahub, mcp, dbt-duckdb |
| `scripts/test_render.py` | ✅ Done | Mock plan rendering test |
| `scripts/test_mcp.py` | ✅ Done | MCP server connection test |
| `scripts/test_week1.sh` | ✅ Done | Week 1 validation |
| `handoff.md` | ✅ This file | Updated Jul 11 |
| `PLAN.md` | ✅ Done | Master build plan |
| `recipes/ingest.yml` | ✅ Done | GMS on port 8080 |
| `examples/*` | ⚠️ Placeholder | Needs real output — Week 3 |

---

## July 11 Coding Session — Bug Fixes and Cleanup

### Model mismatch fix
- `agent/generator.py` was calling `claude-sonnet-4-20250514` (Sonnet 4) but PLAN.md cost story was built on Haiku 4.5 pricing ($1/$5 per M tokens). Changed to `claude-haiku-4-5-20251001` to match.

### Full audit — 16 issues fixed across 17 files

**High severity:**
- `scripts/test_week1.ps1` → renamed to `.sh` (was a Bash script with wrong extension); fixed `call_tool` → `run_tool`, `search_datasets` → `search`, removed misleading `json.dumps` on `None` return
- `LICENSE` — replaced placeholder with full Apache 2.0 text
- `agent/pr.py` — renamed `_get_default_branch_sha` → `_get_default_branch`, fixed return type `tuple[str, str]` → `str`, fixed docstring

**Medium severity:**
- `requirements.txt` — removed unused `boto3`/`sqlglot`, added missing `dbt-duckdb`
- `templates/schema.yml.jinja` — moved `accepted_values`/`relationships` tests from model level to column level; added YAML escaping for description values
- `cli.py` — GMS server URL now reads from `DATAHUB_GMS_URL` env var; output copy filtered to `.sql`/`.yml` only
- `README.md` — added `GITHUB_REPO` env var requirement
- `scripts/run_demo.sh` — added `--skip-pr --skip-writeback` so demo works without external services
- `.github/workflows/ci.yml` — added `agent/**`, `templates/**`, `cli.py`, `requirements.txt` path triggers; added Python deps install step
- `.gitignore` — added `warehouse/target/`, `warehouse/logs/`, `warehouse/dbt_packages/`, `warehouse/.user.yml`

**Low severity:**
- `agent/writeback.py` — removed unused `make_dataset_urn` import
- `scripts/test_render.py` — removed unused `json` import
- `templates/model.sql.jinja` — removed unused `namespace(seen_cols={})`
- `PLAN.md` — removed nonexistent `writeback_screenshot.png`, added test scripts to repo layout, fixed `call_tool` → `run_tool`, updated date and open questions
- `warehouse/dbt_project.yml` — removed `test-paths: ["tests"]` (directory doesn't exist)
- `handoff.md` — corrected test count (27→22), updated file status table

### Verified
- All Python files parse correctly
- Template rendering produces correct output (test_render.py passes)

---

## Key Architecture Decisions

1. **Anthropic API over Claude Code** — `generator.py` uses `anthropic` SDK directly with tool-use. Simpler, more deterministic, full control.
2. **Official MCP SDK** — `mcp` Python SDK v1.28.1 with `anyio` for sync bridge via `asyncio.new_event_loop()`.
3. **DuckDB for warehouse** — Fast, zero-config, dbt-duckdb adapter. Good for demo.
4. **Jinja2 for rendering** — Deterministic output from structured plan JSON.
5. **Unit tests as YAML** — dbt v1.8+ format with `expect:` key and `expect_rows`.
