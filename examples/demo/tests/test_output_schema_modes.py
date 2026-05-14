"""Tests for the `output_schemas` modes of `register_tools`.

The demo server always uses `output_schemas="inline"` (the default), so
this file builds fresh FastMCP apps from the demo handlers in each mode
to exercise `"discovery"` and `"off"` without disturbing the live
`bank2ai_demo.server.app`.
"""

import asyncio
from typing import Any

import pytest
from fastmcp import FastMCP

from bank2ai import register_tools
from bank2ai_demo import server as demo_server


HANDLERS: dict[str, Any] = {
    "get_accounts": demo_server.get_accounts,
    "get_transactions": demo_server.get_transactions,
    "get_transaction": demo_server.get_transaction,
    "get_categories": demo_server.get_categories,
    "get_transactions_summary": demo_server.get_transactions_summary,
    "get_recipients": demo_server.get_recipients,
    "create_recipient": demo_server.create_recipient,
    "prepare_transfer": demo_server.prepare_transfer,
    "execute_transfer": demo_server.execute_transfer,
}

BANK2AI_TOOLS = {
    "get-accounts",
    "get-transactions",
    "get-transaction",
    "get-categories",
    "get-transactions-summary",
    "get-recipients",
    "create-recipient",
    "prepare-transfer",
    "execute-transfer",
}


def _build_app(mode: str) -> FastMCP:
    app = FastMCP(f"test-{mode}")
    register_tools(app, **HANDLERS, output_schemas=mode)
    return app


@pytest.fixture(scope="module")
def discovery_app() -> FastMCP:
    return _build_app("discovery")


@pytest.fixture(scope="module")
def off_app() -> FastMCP:
    return _build_app("off")


@pytest.fixture(scope="module")
def inline_tools_by_name():
    return {t.name: t for t in asyncio.run(demo_server.app.list_tools())}


def test_discovery_strips_output_schemas(discovery_app):
    tools = asyncio.run(discovery_app.list_tools())
    by_name = {t.name: t for t in tools}
    for name in BANK2AI_TOOLS:
        tool = by_name[name]
        assert tool.output_schema is None, (
            f"{name} should have no inline output_schema under discovery mode"
        )


def test_discovery_registers_meta_tool(discovery_app):
    tools = asyncio.run(discovery_app.list_tools())
    by_name = {t.name: t for t in tools}
    assert "describe-tools" in by_name
    describe = by_name["describe-tools"]
    assert describe.output_schema is None
    assert set(describe.parameters.get("properties", {})) == {"tool_names"}


def test_off_strips_output_schemas_and_no_meta_tool(off_app):
    tools = asyncio.run(off_app.list_tools())
    by_name = {t.name: t for t in tools}
    assert "describe-tools" not in by_name
    assert set(by_name) == BANK2AI_TOOLS
    for tool in tools:
        assert tool.output_schema is None


def _call_describe(app: FastMCP, **kwargs):
    result = asyncio.run(app.call_tool("describe-tools", kwargs))
    if hasattr(result, "structured_content"):
        return result.structured_content
    if hasattr(result, "data"):
        return result.data
    return result


def test_describe_tools_default_returns_all_registered(discovery_app):
    payload = _call_describe(discovery_app)
    assert set(payload["schemas"]) == BANK2AI_TOOLS
    for name in BANK2AI_TOOLS:
        assert payload["schemas"][name]["outputSchema"] is not None
        assert payload["schemas"][name]["outputSchema"].get("type") == "object"


def test_describe_tools_subset_and_unknown(discovery_app):
    payload = _call_describe(
        discovery_app,
        tool_names=["get-accounts", "nonexistent-tool"],
    )
    assert set(payload["schemas"]) == {"get-accounts", "nonexistent-tool"}
    assert payload["schemas"]["get-accounts"]["outputSchema"] is not None
    assert payload["schemas"]["nonexistent-tool"]["outputSchema"] is None


def test_describe_tools_matches_inline_shape(discovery_app, inline_tools_by_name):
    """The schema served on demand should describe the same object shape
    FastMCP would have inlined under `output_schemas="inline"` — same
    required-fields contract, so clients see the same model either way."""
    payload = _call_describe(discovery_app)
    for name in BANK2AI_TOOLS:
        inline = inline_tools_by_name[name].output_schema
        served = payload["schemas"][name]["outputSchema"]
        assert inline is not None
        assert served is not None
        # FastMCP may reshape titles / $ref layout, but the top-level
        # required-field set is the response model's contract.
        assert set(inline.get("required", [])) == set(served.get("required", [])), (
            f"{name}: required fields drift between inline and discovery"
        )


def test_discovery_descriptions_advertise_meta_tool(discovery_app, inline_tools_by_name):
    """In discovery mode each bank2ai tool's description must point agents
    at `describe-tools`, so they can find the output schema when they need
    it. Inline mode must not carry the suffix."""
    tools = asyncio.run(discovery_app.list_tools())
    by_name = {t.name: t for t in tools}
    suffix = "describe-tools"
    for name in BANK2AI_TOOLS:
        assert suffix in by_name[name].description, (
            f"{name}: discovery-mode description should mention describe-tools"
        )
        assert suffix not in inline_tools_by_name[name].description, (
            f"{name}: inline-mode description should NOT mention describe-tools"
        )


def test_discovery_does_not_register_unrequested_handlers():
    """Discovery mode must respect the handler-subset rule: tools whose
    handler is omitted are neither listed nor described."""
    app = FastMCP("test-subset")
    register_tools(
        app,
        get_accounts=demo_server.get_accounts,
        get_categories=demo_server.get_categories,
        output_schemas="discovery",
    )
    tools = asyncio.run(app.list_tools())
    by_name = {t.name: t for t in tools}
    assert set(by_name) == {"get-accounts", "get-categories", "describe-tools"}

    payload = _call_describe(app)
    assert set(payload["schemas"]) == {"get-accounts", "get-categories"}
