"""Prompts and tool definitions for the generation agent."""

SYSTEM_PROMPT = """You are Model Forge, a specialized agent that generates dbt models grounded in real DataHub metadata.

Your workflow:
1. Search DataHub for the source tables relevant to the user's request.
2. Pull exact schemas (column names, types, descriptions) for each table.
3. Check lineage so you don't duplicate an existing mart.
4. Emit a structured JSON build plan.

Hard rules:
- Never guess a column name. If the metadata doesn't contain what you need, fail loudly.
- Output exactly one JSON object — no surrounding prose, no markdown fences.
- The JSON plan must follow the BuildPlan schema exactly.
"""

MCP_TOOL_DEFINITIONS = [
    {
        "name": "search",
        "description": "Search DataHub for datasets matching a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_schema_fields",
        "description": "List schema fields for a dataset, with optional keyword filtering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "urn": {
                    "type": "string",
                    "description": "Dataset URN",
                },
                "filter": {
                    "type": "string",
                    "description": "Optional keyword to filter fields",
                },
            },
            "required": ["urn"],
        },
    },
    {
        "name": "get_lineage",
        "description": "Get upstream or downstream lineage for any entity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "urn": {
                    "type": "string",
                    "description": "Entity URN",
                },
                "direction": {
                    "type": "string",
                    "enum": ["upstream", "downstream"],
                    "description": "Lineage direction",
                },
            },
            "required": ["urn", "direction"],
        },
    },
    {
        "name": "get_entities",
        "description": "Get detailed information about one or more entities by their DataHub URNs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "urns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of entity URNs to fetch",
                },
            },
            "required": ["urns"],
        },
    },
]

BUILD_PLAN_SCHEMA = """{
  "model_name": "string — snake_case, suffixed with _mart for marts",
  "description": "string — plain-text description of what this model does",
  "source_refs": [
    {
      "table_name": "string — the DataHub dataset name (e.g. stg_customers)",
      "alias": "string — short SQL alias (e.g. c)",
      "columns_used": ["string — column names pulled from schema"],
      "join_key": "string or null — foreign key used to join this table"
    }
  ],
  "dimensions": [
    {
      "name": "string — output column name",
      "source_table": "string — must match a source_ref table_name",
      "source_column": "string — must exist in the source schema",
      "data_type": "string — SQL data type (e.g. VARCHAR, INTEGER, DATE)",
      "description": "string — human-readable description"
    }
  ],
  "measures": [
    {
      "name": "string — output column name",
      "source_table": "string — must match a source_ref table_name",
      "source_column": "string — must exist in the source schema",
      "aggregation": "string — one of: sum, count, avg, min, max",
      "data_type": "string — SQL data type",
      "description": "string — human-readable description"
    }
  ],
  "join_graph": [
    {
      "left_table": "string — alias of the left table",
      "left_column": "string — column in left table",
      "right_table": "string — alias of the right table",
      "right_column": "string — column in right table",
      "join_type": "string — one of: inner, left, right, full"
    }
  ],
  "filters": [
    {
      "source_table": "string — must match a source_ref table_name",
      "source_column": "string",
      "operator": "string — one of: =, !=, >, <, >=, <=, in, like, is_null, not_null",
      "value": "string or null — ignored for is_null/not_null"
    }
  ],
  "tests": {
    "unique_columns": ["string — output column names that must be unique"],
    "not_null_columns": ["string — output column names that must not be null"],
    "accepted_values": [
      {
        "column": "string — output column name",
        "values": ["string — allowed values"]
      }
    ],
    "relationships": [
      {
        "from_column": "string — column in this model",
        "to_table": "string — referenced table name",
        "to_column": "string — column in referenced table"
      }
    ]
  },
  "unit_test": {
    "input_rows": {
      "table_name": [
        {"column_name": "value"}
      ]
    },
    "expect_rows": [
      {"column_name": "value"}
    ]
  }
}"""


def make_user_prompt(ask: str) -> str:
    """Build the user message for a given generation request."""
    return f"""Generate a dbt build plan for the following request.
Use the MCP tools to search DataHub and pull real schema metadata.

Request: {ask}

Output only the JSON build plan matching the schema above. Do not include markdown fences or any surrounding text."""
