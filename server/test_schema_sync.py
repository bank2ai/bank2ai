"""Tests that JSON schemas, Pydantic models, MCP tool definitions, and adapter
interface stay in sync.

Run from the server/ directory:
    pytest test_schema_sync.py -v
"""

import inspect
import json
from pathlib import Path
from typing import get_type_hints

import pytest

from adapters.base import BankAdapter
from adapters.models import Account, Category, Receipient, Transaction

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

# Map each JSON schema file to its Pydantic model
SCHEMA_MODEL_PAIRS = [
    ("account.json", Account),
    ("transaction.json", Transaction),
    ("recipient.json", Receipient),
    ("category.json", Category),
]


# ---------------------------------------------------------------------------
# 1. JSON schemas ↔ Pydantic models
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("schema_file, model", SCHEMA_MODEL_PAIRS, ids=lambda x: x if isinstance(x, str) else x.__name__)
def test_model_has_all_schema_fields(schema_file, model):
    """Every property in a JSON schema must exist as a field on the Pydantic model."""
    schema = json.loads((SCHEMA_DIR / schema_file).read_text())
    schema_props = set(schema.get("properties", {}).keys())
    model_fields = set(model.model_fields.keys())

    missing = schema_props - model_fields
    assert not missing, (
        f"{model.__name__} is missing fields defined in {schema_file}: {missing}"
    )


@pytest.mark.parametrize("schema_file, model", SCHEMA_MODEL_PAIRS, ids=lambda x: x if isinstance(x, str) else x.__name__)
def test_model_has_no_extra_fields(schema_file, model):
    """Pydantic model should not have fields absent from the JSON schema."""
    schema = json.loads((SCHEMA_DIR / schema_file).read_text())
    schema_props = set(schema.get("properties", {}).keys())
    model_fields = set(model.model_fields.keys())

    extra = model_fields - schema_props
    assert not extra, (
        f"{model.__name__} has fields not in {schema_file}: {extra}"
    )


@pytest.mark.parametrize("schema_file, model", SCHEMA_MODEL_PAIRS, ids=lambda x: x if isinstance(x, str) else x.__name__)
def test_required_fields_match(schema_file, model):
    """Fields marked required in JSON schema must be required in the Pydantic model."""
    schema = json.loads((SCHEMA_DIR / schema_file).read_text())
    schema_required = set(schema.get("required", []))

    model_required = set()
    for name, field_info in model.model_fields.items():
        if field_info.is_required():
            model_required.add(name)

    missing_required = schema_required - model_required
    assert not missing_required, (
        f"{model.__name__} should require {missing_required} (required in {schema_file})"
    )


# ---------------------------------------------------------------------------
# 2. MCP tool inputSchemas ↔ BankAdapter method signatures
# ---------------------------------------------------------------------------

# Map tool name → adapter method name and any parameter renames
# (tool schema key → adapter method kwarg)
TOOL_METHOD_MAP = {
    "get-accounts": {
        "method": "get_accounts",
        "param_map": {"only_withdrawal_accounts": "only_withdrawal"},
    },
    "transactions": {
        "method": "get_transactions",
        "param_map": {},
    },
    "get-categories": {
        "method": "get_categories",
        "param_map": {},
    },
    "spending-summary": {
        "method": "get_spending_summary",
        "param_map": {},
    },
    "recipients-by-name": {
        "method": "search_recipients",
        "param_map": {},
    },
    "create-recipient": {
        "method": "create_recipient",
        "param_map": {},
    },
    "transfer-money-icelandic": {
        "method": "prepare_transfer",
        "param_map": {"recipient_ssn": "recipient_ssn"},
    },
    "execute-transfer": {
        "method": "execute_transfer",
        "param_map": {},
    },
}


def _get_tools_by_name() -> dict:
    """Import server module and return tools keyed by name."""
    import server
    tools = server.app._tool_manager.list_tools()
    # Expose `inputSchema` (matches MCP wire shape) on top of FastMCP's `parameters`.
    return {t.name: type("ToolView", (), {"name": t.name, "inputSchema": t.parameters})() for t in tools}


def _get_adapter_params(method_name: str) -> set[str]:
    """Get parameter names for a BankAdapter method (excluding self)."""
    method = getattr(BankAdapter, method_name)
    sig = inspect.signature(method)
    return {p for p in sig.parameters if p != "self"}


@pytest.fixture(scope="module")
def tools_by_name():
    return _get_tools_by_name()


@pytest.mark.parametrize("tool_name", list(TOOL_METHOD_MAP.keys()))
def test_tool_params_covered_by_adapter(tools_by_name, tool_name):
    """Every tool inputSchema property must map to an adapter method parameter."""
    mapping = TOOL_METHOD_MAP[tool_name]
    tool = tools_by_name[tool_name]
    tool_props = set(tool.inputSchema.get("properties", {}).keys())
    adapter_params = _get_adapter_params(mapping["method"])
    param_map = mapping.get("param_map", {})

    for prop in tool_props:
        mapped = param_map.get(prop, prop)
        assert mapped in adapter_params, (
            f"Tool '{tool_name}' has property '{prop}' (mapped to '{mapped}') "
            f"but BankAdapter.{mapping['method']} has no such parameter. "
            f"Available: {adapter_params}"
        )


@pytest.mark.parametrize("tool_name", list(TOOL_METHOD_MAP.keys()))
def test_adapter_has_method(tool_name):
    """Every tool must have a corresponding method on BankAdapter."""
    method_name = TOOL_METHOD_MAP[tool_name]["method"]
    assert hasattr(BankAdapter, method_name), (
        f"BankAdapter is missing method '{method_name}' for tool '{tool_name}'"
    )


def test_all_tools_have_mapping(tools_by_name):
    """Every tool defined in server.py must have an entry in TOOL_METHOD_MAP."""
    unmapped = set(tools_by_name.keys()) - set(TOOL_METHOD_MAP.keys())
    assert not unmapped, (
        f"Tools without adapter mapping: {unmapped}. "
        f"Add entries to TOOL_METHOD_MAP in test_schema_sync.py."
    )
