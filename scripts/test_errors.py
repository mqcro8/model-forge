"""Test fail-fast error handling — no external dependencies required."""
import sys
import types
sys.path.insert(0, ".")

# Stub out anthropic so generator.py can be imported without it installed
_stub = types.ModuleType("anthropic")
_stub.Anthropic = type("Anthropic", (), {})
_stub.APIError = type("APIError", (Exception,), {})
_stub.APITimeoutError = type("APITimeoutError", (_stub.APIError,), {})
_stub.APIConnectionError = type("APIConnectionError", (_stub.APIError,), {})
sys.modules.setdefault("anthropic", _stub)

from agent.generator import GenerationError, _validate_plan
from agent.mcp_client import MCPError


def test_generation_error():
    exc = GenerationError("test error")
    assert str(exc) == "test error"
    print("  GenerationError: OK")


def test_mcp_error():
    exc = MCPError("mcp failure")
    assert str(exc) == "mcp failure"
    print("  MCPError: OK")


def test_validate_plan_ok():
    plan = {
        "model_name": "test_mart",
        "description": "test",
        "source_refs": [{"table_name": "t", "alias": "a", "columns_used": [], "join_key": None}],
        "dimensions": [{"name": "id", "source_table": "t", "source_column": "id", "data_type": "INT", "description": "id"}],
        "measures": [],
        "join_graph": [],
        "tests": [],
        "unit_test": {"input_rows": {}, "expect_rows": []},
    }
    _validate_plan(plan)
    print("  validate_plan (valid): OK")


def test_validate_plan_missing_keys():
    try:
        _validate_plan({"model_name": "x"})
        assert False, "Should have raised"
    except GenerationError as e:
        assert "missing required keys" in str(e)
    print("  validate_plan (missing keys): OK")


def test_validate_plan_missing_new_keys():
    """Missing unit_test should raise; join_graph/tests default to empty."""
    base = {
        "model_name": "x", "description": "x",
        "source_refs": [{"table_name": "t", "alias": "a", "columns_used": [], "join_key": None}],
        "dimensions": [{"name": "a", "source_table": "t", "source_column": "a", "data_type": "INT", "description": "a"}],
        "measures": [],
    }
    # unit_test is required
    try:
        _validate_plan(dict(base))
        assert False, "Should have raised for missing unit_test"
    except GenerationError as e:
        assert "missing required keys" in str(e) and "unit_test" in str(e)

    # join_graph and tests should default, not raise
    plan = {**base, "unit_test": {"input_rows": {}, "expect_rows": []}}
    _validate_plan(plan)
    assert plan["join_graph"] == []
    assert plan["tests"]["unique_columns"] == []
    print("  validate_plan (missing unit_test raises, others default): OK")


def test_validate_plan_missing_optional_keys():
    """Plan with required keys but missing optional keys should auto-default them."""
    plan = {
        "model_name": "test_mart",
        "description": "test",
        "source_refs": [{"table_name": "t", "alias": "a", "columns_used": [], "join_key": None}],
        "dimensions": [{"name": "id", "source_table": "t", "source_column": "id", "data_type": "INT", "description": "id"}],
        "measures": [],
        "unit_test": {"input_rows": {}, "expect_rows": []},
    }
    _validate_plan(plan)
    # Optional keys should be defaulted
    assert plan["join_graph"] == []
    assert plan["filters"] == []
    assert plan["tests"] == {"unique_columns": [], "not_null_columns": [], "accepted_values": [], "relationships": []}
    print("  validate_plan (missing optional keys defaulted): OK")


def test_validate_plan_no_sources():
    try:
        _validate_plan({
            "model_name": "x", "description": "x", "source_refs": [],
            "dimensions": [{"name": "a", "source_table": "t", "source_column": "a", "data_type": "INT", "description": "a"}],
            "measures": [],
            "join_graph": [], "tests": [], "unit_test": {"input_rows": {}, "expect_rows": []},
        })
        assert False, "Should have raised"
    except GenerationError as e:
        assert "no source_refs" in str(e)
    print("  validate_plan (empty sources): OK")


def test_validate_plan_empty():
    try:
        _validate_plan({
            "model_name": "x", "description": "x",
            "source_refs": [{"table_name": "t", "alias": "a", "columns_used": [], "join_key": None}],
            "dimensions": [], "measures": [],
            "join_graph": [], "tests": [], "unit_test": {"input_rows": {}, "expect_rows": []},
        })
        assert False, "Should have raised"
    except GenerationError as e:
        assert "no dimensions or measures" in str(e)
    print("  validate_plan (empty dimensions+measures): OK")


if __name__ == "__main__":
    print("Testing fail-fast error handling...")
    test_generation_error()
    test_mcp_error()
    test_validate_plan_ok()
    test_validate_plan_missing_keys()
    test_validate_plan_missing_new_keys()
    test_validate_plan_missing_optional_keys()
    test_validate_plan_no_sources()
    test_validate_plan_empty()
    print("\nAll tests passed.")
