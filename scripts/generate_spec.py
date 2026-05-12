"""Regenerate the language-neutral bank2ai MCP spec.

Reads the FastMCP tool registrations from the ``bank2ai-demo`` reference
implementation (which exposes the full bank2ai surface without auth) plus
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
    AccountNumberIdentifier,
    AliasIdentifier,
    Balance,
    BbanIdentifier,
    Category,
    ConfirmationOfPayee,
    ExecutedTransfer,
    IbanIdentifier,
    NationalId,
    Party,
    PreparedTransfer,
    Recipient,
    RemittanceInformation,
    Transaction,
    TransactionCode,
    TransactionsSummaryGroup,
    TransactionsSummaryPeriod,
    TransferAction,
    TransferFee,
    TransferFx,
    TransferSummary,
    TransferWarning,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "specs" / "bank2ai.json"
SPEC_VERSION = "0.11.0"

DOCUMENTED_MODELS = {
    "Account": Account,
    "Transaction": Transaction,
    "Category": Category,
    "Recipient": Recipient,
}

# Auxiliary Pydantic shapes that aren't part of the four documented
# models but appear inlined inside tool input / output schemas
# (FastMCP flattens response models, dropping titles, so this registry
# is what lets the docs tooling label inlined occurrences by name).
# Not part of the user-facing model surface; the spec narrative still
# documents only the four entries in `models`.
COMPONENT_MODELS = {
    "AccountNumberIdentifier": AccountNumberIdentifier,
    "AliasIdentifier": AliasIdentifier,
    "Balance": Balance,
    "BbanIdentifier": BbanIdentifier,
    "ConfirmationOfPayee": ConfirmationOfPayee,
    "ExecutedTransfer": ExecutedTransfer,
    "IbanIdentifier": IbanIdentifier,
    "NationalId": NationalId,
    "Party": Party,
    "PreparedTransfer": PreparedTransfer,
    "RemittanceInformation": RemittanceInformation,
    "TransactionCode": TransactionCode,
    "TransactionsSummaryGroup": TransactionsSummaryGroup,
    "TransactionsSummaryPeriod": TransactionsSummaryPeriod,
    "TransferAction": TransferAction,
    "TransferFee": TransferFee,
    "TransferFx": TransferFx,
    "TransferSummary": TransferSummary,
    "TransferWarning": TransferWarning,
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


def _collect_component_schemas() -> dict[str, Any]:
    return {
        name: model.model_json_schema()
        for name, model in sorted(COMPONENT_MODELS.items())
    }


def build_spec() -> dict[str, Any]:
    """Build the full spec dict. Pure function, no I/O."""
    tools = asyncio.run(_collect_tools())
    return {
        "$schema": "https://bank2ai.com/specs/bank2ai.schema.json",
        "version": SPEC_VERSION,
        "tools": tools,
        "models": _collect_models(),
        "componentSchemas": _collect_component_schemas(),
    }


def write_spec(spec: dict[str, Any]) -> None:
    SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(spec, indent=2, sort_keys=True) + "\n"
    SPEC_PATH.write_text(serialized)


def main() -> int:
    spec = build_spec()
    write_spec(spec)
    print(
        f"Wrote {SPEC_PATH.relative_to(REPO_ROOT)} "
        f"({len(spec['tools'])} tools, {len(spec['models'])} models, "
        f"{len(spec['componentSchemas'])} component schemas)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
