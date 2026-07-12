"""Test template rendering with a mock build plan."""
from pathlib import Path
from agent.render import render_model

# Mock plan matching what the generator would produce for a customer LTV mart
mock_plan = {
    "model_name": "customer_ltv_mart",
    "description": "Customer lifetime value mart aggregating total spend and order counts per customer",
    "source_refs": [
        {
            "table_name": "stg_customers",
            "alias": "c",
            "columns_used": ["customer_id", "first_name", "last_name", "email", "country"],
            "join_key": "customer_id",
        },
        {
            "table_name": "stg_orders",
            "alias": "o",
            "columns_used": ["customer_id", "order_id", "order_status", "total_amount", "order_date"],
            "join_key": "customer_id",
        },
    ],
    "dimensions": [
        {
            "name": "customer_id",
            "source_table": "stg_customers",
            "source_column": "customer_id",
            "data_type": "INTEGER",
            "description": "Unique customer identifier",
        },
        {
            "name": "customer_name",
            "source_table": "stg_customers",
            "source_column": "first_name",
            "data_type": "VARCHAR",
            "description": "Customer first name",
        },
        {
            "name": "country",
            "source_table": "stg_customers",
            "source_column": "country",
            "data_type": "VARCHAR",
            "description": "Customer country",
        },
    ],
    "measures": [
        {
            "name": "total_spend",
            "source_table": "stg_orders",
            "source_column": "total_amount",
            "aggregation": "sum",
            "data_type": "DOUBLE",
            "description": "Total amount spent across all orders",
        },
        {
            "name": "order_count",
            "source_table": "stg_orders",
            "source_column": "order_id",
            "aggregation": "count",
            "data_type": "INTEGER",
            "description": "Total number of orders placed",
        },
    ],
    "join_graph": [
        {
            "left_table": "c",
            "left_column": "customer_id",
            "right_table": "o",
            "right_column": "customer_id",
            "join_type": "left",
        }
    ],
    "filters": [
        {
            "source_table": "stg_orders",
            "source_column": "order_status",
            "operator": "=",
            "value": "'completed'",
        }
    ],
    "tests": {
        "unique_columns": ["customer_id"],
        "not_null_columns": ["customer_id", "customer_name", "total_spend", "order_count"],
        "accepted_values": [],
        "relationships": [],
    },
    "unit_test": {
        "input_rows": {
            "stg_customers": [
                {"customer_id": 1, "first_name": "Alice", "last_name": "Smith", "email": "alice@example.com", "country": "US"},
            ],
            "stg_orders": [
                {"order_id": 1001, "customer_id": 1, "order_status": "completed", "total_amount": 150.00},
                {"order_id": 1002, "customer_id": 1, "order_status": "completed", "total_amount": 200.00},
            ],
        },
        "expect_rows": [
            {"customer_id": 1, "customer_name": "Alice", "country": "US", "total_spend": 350.00, "order_count": 2},
        ],
    },
}

output_dir = Path("output/test")
paths = render_model(mock_plan, output_dir)

for key, path in paths.items():
    print(f"\n{'='*60}")
    print(f"FILE: {path}")
    print(f"{'='*60}")
    print(path.read_text(encoding="utf-8"))
