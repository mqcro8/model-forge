"""Prompts for the generation agent."""

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

BUILD_PLAN_SCHEMA = """{
  "model_name": "string — snake_case, suffixed with _mart for marts",
  "description": "string — plain-text description of what this model does",
  "source_refs": [
    {
      "table_name": "string (e.g. customers)",
      "alias": "string (e.g. c)",
      "columns_used": ["string column names"],
      "join_key": "string or null"
    }
  ],
  "dimensions": [
    {
      "name": "string column name in output",
      "source_table": "string",
      "source_column": "string",
      "data_type": "string",
      "description": "string"
    }
  ],
  "measures": [
    {
      "name": "string column name in output",
      "source_table": "string",
      "source_column": "string",
      "aggregation": "string (sum, count, avg, min, max)",
      "data_type": "string",
      "description": "string"
    }
  ],
  "join_graph": [
    {
      "left_table": "string",
      "left_column": "string",
      "right_table": "string",
      "right_column": "string",
      "join_type": "string (inner, left, right, full)"
    }
  ],
  "filters": [
    {
      "source_table": "string",
      "source_column": "string",
      "operator": "string (=, !=, >, <, >=, <=, in, like, is_null, not_null)",
      "value": "string or null"
    }
  ],
  "tests": {
    "unique_columns": ["string column names"],
    "not_null_columns": ["string column names"],
    "accepted_values": [
      {
        "column": "string",
        "values": ["string"]
      }
    ],
    "relationships": [
      {
        "from_column": "string",
        "to_table": "string",
        "to_column": "string"
      }
    ]
  },
  "unit_test": {
    "input_rows": {
      "table_name": [
        {"column": "value", ...}
      ]
    },
    "expected_output_rows": [
      {"column": "value", ...}
    ]
  }
}"""


def make_user_prompt(ask: str) -> str:
    """Build the user message for a given generation request."""
    return f"""Generate a dbt build plan for the following request.
Use the MCP search and schema tools to ground your answer in real DataHub metadata.

Request: {ask}

Output only the JSON build plan matching the schema above."""
