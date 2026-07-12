# Model Forge — build plan

**Build with DataHub: The Agent Hackathon** — submission plan
Category: Metadata-Aware Code Generation & Development
Submission deadline: **August 10, 2026, 5:00pm ET**

---

## 1. The idea

An agent that reads real schema and lineage from a self-hosted DataHub instance
through the MCP Server, plans a `dbt` model against that real metadata (not
guessed columns), renders it, proves it works by actually running `dbt build`
against a small local warehouse, opens a GitHub PR, and writes an annotation
back onto the source tables in DataHub.

Scope is deliberately narrow: **one pattern, built well** — a customer LTV
mart — not five patterns built shakily.

Why this scope: it targets the Metadata-Aware Code Generation category
directly, and because the agent both calls MCP tools *and* writes back to the
graph, it also scores on the "Use of DataHub" criterion, which explicitly
rewards submissions that go beyond reading metadata.

---

## 2. Cost breakdown — target $0

| Component | Tool | Cost |
|---|---|---|
| Catalog | DataHub Core, self-hosted via `datahub docker quickstart` | $0 — Apache 2.0 open source |
| Container runtime | Docker Desktop, or a free alternative | $0 — Podman Desktop / Rancher Desktop if you'd rather avoid Docker Desktop's license |
| Metadata access | `mcp-server-datahub` (self-hosted MCP server) | $0 — open source |
| Dev tooling | DataHub Skills in Claude Code | $0 — open source, free under an existing Claude Code subscription |
| Transform layer | dbt-core + dbt-duckdb adapter | $0 — both open source, no warehouse account needed |
| Source control / CI | GitHub public repo + Actions | $0 — free minutes on public repos |
| The "brain" | Claude Haiku 4.5 via API | ~$0–1 total. $1 / $5 per million input/output tokens. Each generation call is ~10–20k tokens of schema context — a few cents a run |
| Demo hosting | none needed | $0 — judges run it locally from the README |

Literal-$0 alternative: drive the same agent loop through Claude Code in
headless mode (`claude -p "..."`) using an existing subscription instead of
the API. Same architecture, different execution engine. Default recommendation
is still the API path above — it's the more portable, judge-runnable version
and costs pennies.

---

## 3. Architecture

Five-stage pipeline, one direction, plus one feedback loop:

1. **DataHub** — holds schema, lineage, glossary for the project's tables.
2. **MCP server** (`mcp-server-datahub`) — exposes DataHub as callable tools:
   search, get dataset metadata, list schema fields, trace lineage.
3. **Generation agent** (Claude) — calls those tools to ground itself, then
   emits a structured build plan (not raw SQL prose).
4. **dbt build (duckdb)** — a deterministic renderer turns the plan into
   `model.sql` + `schema.yml` + a unit test, then actually runs and tests it
   locally.
5. **GitHub PR + CI** — the passing model is committed, a PR opens, CI
   re-runs `dbt build` to confirm it from a clean checkout.

**Feedback loop:** after the PR step, the agent writes back onto DataHub —
descriptions/tags on the source tables and (ideally) explicit column-level
lineage — so the graph reflects what the agent just built. This write-back
step is not decoration; it's what separates this from a plain text-to-SQL
wrapper and is called out by name in the judging criteria.

**Important design note:** don't rely only on DataHub's `showcase-ecommerce`
demo pack for source metadata — it's rich, but metadata-only (no real
warehouse sits behind those Snowflake/Looker entities). Instead, seed a tiny
dbt-duckdb project yourself (customers, orders, order_items — 3–4 tables),
ingest *that* into DataHub with its `dbt` connector, and now the schema the
agent reads is the exact schema `dbt build` executes against. That's the
difference between a demo that looks right and one that survives a judge
actually running it.

---

## 4. Repo layout

```
model-forge/
├── README.md                  # setup + how judges test it in <5 min
├── LICENSE                    # Apache 2.0 (required by the hackathon rules)
├── .github/workflows/ci.yml   # runs dbt build on every PR
├── agent/
│   ├── mcp_client.py          # launches/talks to mcp-server-datahub over stdio
│   ├── generator.py           # Claude tool-use loop -> structured build plan
│   ├── prompts.py
│   ├── render.py               # Jinja: plan -> model.sql + schema.yml + unit test
│   ├── writeback.py            # DataHub SDK: annotate source tables post-build
│   └── pr.py                   # opens branch + PR via GitHub API
├── templates/
│   ├── model.sql.jinja
│   ├── schema.yml.jinja
│   └── unit_test.jinja
├── warehouse/                  # the tiny seed dbt-duckdb project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── seeds/ (customers.csv, orders.csv, order_items.csv)
│   └── models/staging/
├── examples/                   # judges can look here without running anything
│   ├── prompt.txt
│   ├── generated_model.sql
│   └── generated_schema.yml
├── scripts/
│   ├── setup_datahub.sh
│   ├── run_demo.sh
│   ├── test_render.py
│   ├── test_mcp.py
│   └── test_week1.sh
└── cli.py                      # entry point: `python cli.py generate "<ask>"`
```

---

## 5. The one correct path (no fallbacks, fail fast)

1. **Local DataHub up.**
   `datahub docker quickstart` — full stack in under two minutes on Docker.

2. **Seed the warehouse.**
   `dbt seed && dbt run && dbt docs generate` inside `warehouse/` using
   dbt-duckdb — produces real `manifest.json` / `catalog.json` from an
   actually-runnable project.

3. **Ingest it.**
   A `dbt` source recipe pointed at those artifacts — `manifest_path`,
   `catalog_path`, and `target_platform` are the required fields. Real
   schema, real lineage, now in DataHub.

4. **Connect the MCP server.**
   `uvx mcp-server-datahub@latest` against the local GMS URL.
   `mcp_client.py` is a thin wrapper that launches this over stdio and
   exposes `run_tool()`. The server's read-only discovery tools (search,
   pull full metadata, drill into schemas, trace lineage) are always on;
   its mutation tools (tags, glossary terms, ownership) only activate once
   `TOOLS_IS_MUTATION_ENABLED=true` is set — keep that off for the read
   path and on only for `writeback.py`.

5. **Generate.**
   `generator.py` gives Claude the MCP tool definitions as custom tools and
   runs a short loop: search for the relevant tables → pull exact
   columns/types → check lineage so it doesn't duplicate an existing mart →
   emit a structured JSON build plan.
   If DataHub or the MCP server is unreachable, or a needed table isn't
   found — **throw, don't guess.** A generator that silently falls back to
   plausible-looking column names is worse than one that fails loudly.

6. **Render deterministically.**
   `render.py` fills the three Jinja templates from the structured plan.
   The LLM writes the SQL; the template — not the LLM — guarantees the YAML
   is syntactically valid dbt config. This is the root-cause fix for "LLM
   hallucinates malformed YAML," not a runtime retry.

7. **Prove it.**
   `dbt build --select <model>` against the local DuckDB file. If it fails,
   stop — don't open a PR for something that doesn't build.

8. **Ship it.**
   `pr.py` opens a branch, commits the three generated files, opens a PR
   with a description listing exactly which DataHub tables/columns it
   grounded on.

9. **Close the loop.**
   `writeback.py` flips mutation mode on just for this call and adds a
   description/tag to the source dataset(s) noting the new derived model —
   plus, ideally, an explicit `add_lineage()` call so the new mart shows up
   downstream of its real sources in the graph.

**For your own local dev exploration** (not part of the shipped product):
install DataHub Skills into Claude Code once —
`claude plugin install datahub-skills`, then run
`/datahub-skills:datahub-setup` to point it at the local instance. Gives
`/datahub-search`, `/datahub-lineage`, etc. right inside coding sessions
while building the generator itself.

---

## 6. Timeline

Today: July 11, 2026. Submissions close August 10, 2026, 5:00pm ET — about
4 weeks.

| Week | Dates | Milestone | Status |
|---|---|---|---|
| 1 | Jul 9–15 | DataHub up, seed warehouse ingested, MCP server talking to it. Confirm `search` / `list_schema_fields` / `get_lineage` all return real data. | ✅ DONE |
| 2 | Jul 16–22 | Build the generator loop + templates. Milestone: one prompt → one `dbt build`-passing model, end to end. | ✅ DONE |
| 3 | Jul 23–29 | Write-back, PR automation, CI workflow, `examples/` folder, harden fail-fast paths. | 🔄 IN PROGRESS (3.1, 3.2, 3.4 done; 3.3, 3.5 pending) |
| 4 | Jul 30–Aug 5 | README, demo video (≤3 min, must show it actually running), optional OSS bonus contribution, clean-clone test run. | ⬜ PENDING |
| — | Aug 6–10 | Buffer, submit. | ⬜ PENDING |

---

## 7. Kickoff brief — paste this to the coding agent

```
Build "Model Forge": an agent that generates a dbt model grounded in real
DataHub metadata. Read the repo layout and build steps below before writing
anything.

Hard rules:
- One path, no fallback templates. If DataHub/MCP is unreachable or a table
  isn't found, raise an exception with a clear message — never guess a
  column name.
- The LLM never writes raw YAML. It emits a structured JSON plan; render.py
  fills Jinja templates deterministically.
- Every generation run must end with either (a) a passing `dbt build` + PR
  + DataHub write-back, or (b) a clear thrown error. No partial silent state.

Start with warehouse/ (seed dbt-duckdb project: customers, orders,
order_items), then agent/mcp_client.py, then the generation loop.
```

---

## 8. Where the bonus points are

The hackathon rules explicitly reward "meaningful open-source contributions
to DataHub — new connectors, skills, fixes, RFCs, or documentation
improvements." The `datahub-skills` repo is set up for exactly this kind of
contribution — if there's a spare day in week 4, a small real PR there (even
a docs fix showing this code-gen pattern) counts toward the bonus.

---

## 9. Open questions / next steps

- [x] Scaffold the repo (seed dbt project, MCP client, Jinja templates)
- [x] Write the `dbt` ingestion recipe and confirm DataHub is reading the
      real seed-project schema before any agent code exists
- [x] Decide: Anthropic API key vs. Claude Code headless mode for the
      generation agent's execution engine — using Anthropic API (Haiku 4.5)
- [x] Pick the exact LTV definition/aggregation logic for the demo model
- [ ] Fail-fast hardening (3.3) — timeouts, stderr collection, error paths
- [ ] Examples folder — replace placeholders with real generated output
