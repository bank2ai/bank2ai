"""Tests that the registered MCP tool surface matches the bank2ai spec.

Run from the examples/demo directory:
    pytest -v
"""

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

from bank2ai_demo import server as demo_server


REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = REPO_ROOT / "specs" / "bank2ai.json"
GENERATOR_PATH = REPO_ROOT / "scripts" / "generate_spec.py"


def _load_generator():
    """Import scripts/generate_spec.py without putting it on sys.path."""
    spec = importlib.util.spec_from_file_location("generate_spec", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# register_tools produces the full bank2ai surface with the right inputs
# ---------------------------------------------------------------------------

EXPECTED_TOOL_INPUTS = {
    "get-accounts": {"only_withdrawal_accounts", "account_type"},
    "get-transactions": {
        "count", "order", "start_date", "end_date",
        "description", "categories", "account_ids",
        "min_amount", "max_amount", "cursor",
    },
    "get-categories": set(),
    "transactions-summary": {
        "direction", "group_by", "start_date", "end_date",
        "categories", "account_ids", "min_amount", "max_amount",
    },
    "recipients-by-name": {"name"},
    "create-recipient": {"name", "account_number", "kennitala"},
    "transfer-money-icelandic": {
        "amount", "recipient_ssn", "recipient_account_number",
        "description", "withdrawal_account_number", "currency",
    },
    "execute-transfer": {
        "withdrawal_account_id", "recipient_account_number", "amount", "description",
    },
}


@pytest.fixture(scope="module")
def tools_by_name():
    return {t.name: t for t in asyncio.run(demo_server.app.list_tools())}


def test_all_expected_tools_registered(tools_by_name):
    assert set(tools_by_name) == set(EXPECTED_TOOL_INPUTS)


@pytest.mark.parametrize("tool_name, expected_props", list(EXPECTED_TOOL_INPUTS.items()))
def test_tool_input_properties(tools_by_name, tool_name, expected_props):
    tool = tools_by_name[tool_name]
    actual = set(tool.parameters.get("properties", {}).keys())
    assert actual == expected_props, (
        f"{tool_name}: expected input properties {expected_props}, got {actual}"
    )


@pytest.mark.parametrize("tool_name", list(EXPECTED_TOOL_INPUTS.keys()))
def test_tool_has_object_output_schema(tools_by_name, tool_name):
    """Every bank2ai tool exposes an object output schema (inferred by FastMCP
    from the Pydantic response-model annotation)."""
    tool = tools_by_name[tool_name]
    assert tool.output_schema is not None, f"{tool_name} missing output_schema"
    assert tool.output_schema.get("type") == "object"


# ---------------------------------------------------------------------------
# specs/bank2ai.json stays in sync with the Python reference implementation
# ---------------------------------------------------------------------------

def test_committed_spec_matches_generator():
    generator = _load_generator()
    generated = generator.build_spec()
    committed = json.loads(SPEC_PATH.read_text())
    assert generated == committed, (
        "specs/bank2ai.json is stale. Run `uv run python scripts/generate_spec.py`."
    )
