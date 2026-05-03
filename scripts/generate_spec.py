"""Regenerate the language-neutral Bank2AI MCP spec.

Reads the FastMCP tool registrations from the ``bank2ai-demo`` reference
implementation (which exposes the full Bank2AI surface without auth) plus
the shared Pydantic models from ``bank2ai.models``, and writes a
JSON-Schema-based spec to ``specs/bank2ai.json``.

The Python package is currently the source of truth; this script keeps the
spec in sync. A drift test in ``examples/demo/tests/test_schema_sync.py``
re-runs ``build_spec`` in-memory and asserts equality with the committed
file, so changes to the Python package can't silently desync the spec.

Usage:
    uv run python scripts/generate_spec.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from bank2ai_demo.server import app
from bank2ai.models import (
    Account,
    AuthParam,
    AuthResponse,
    Category,
    Receipient,
    Transaction,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "specs" / "bank2ai.json"
SPEC_VERSION = "0.1.0"

DOCUMENTED_MODELS = {
    "Account": Account,
    "Transaction": Transaction,
    "Category": Category,
    "Receipient": Receipient,
    "AuthParam": AuthParam,
    "AuthResponse": AuthResponse,
}

VENDOR_PREFIXES = ("x-fastmcp-",)


def _strip_vendor_keys(node: Any) -> Any:
    """Remove implementation-specific JSON Schema extensions (e.g. ``x-fastmcp-*``)."""
    if isinstance(node, dict):
        return {
            key: _strip_vendor_keys(value)
            for key, value in node.items()
            if not any(key.startswith(prefix) for prefix in VENDOR_PREFIXES)
        }
    if isinstance(node, list):
        return [_strip_vendor_keys(item) for item in node]
    return node


async def _collect_tools() -> list[dict[str, Any]]:
    tools = await app.list_tools()
    rows: list[dict[str, Any]] = []
    for tool in sorted(tools, key=lambda t: t.name):
        rows.append({
            "name": tool.name,
            "description": tool.description,
            "inputSchema": _strip_vendor_keys(tool.parameters),
            "outputSchema": _strip_vendor_keys(tool.output_schema or {}),
        })
    return rows


def _collect_models() -> dict[str, Any]:
    return {
        name: model.model_json_schema()
        for name, model in sorted(DOCUMENTED_MODELS.items())
    }


def build_spec() -> dict[str, Any]:
    """Build the full spec dict. Pure function — no I/O."""
    tools = asyncio.run(_collect_tools())
    return {
        "$schema": "https://bank2ai.com/specs/bank2ai.schema.json",
        "version": SPEC_VERSION,
        "auth": {
            "protocol": "elicit-or-authenticate-tool",
            "description": (
                "If the bank requires credentials, the server MUST expose an "
                "`authenticate` tool whose JSON Schema is built from the "
                "`required_parameters` returned by an unauthenticated AuthResponse. "
                "Clients that support MCP elicitation MAY collect the same "
                "credentials inline. See bank2ai.spec.md for the full protocol."
            ),
        },
        "tools": tools,
        "models": _collect_models(),
    }


def write_spec(spec: dict[str, Any]) -> None:
    SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(spec, indent=2, sort_keys=True) + "\n"
    SPEC_PATH.write_text(serialized)


def main() -> int:
    spec = build_spec()
    write_spec(spec)
    print(f"Wrote {SPEC_PATH.relative_to(REPO_ROOT)} ({len(spec['tools'])} tools, {len(spec['models'])} models)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
