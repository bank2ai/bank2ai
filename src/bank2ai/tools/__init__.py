"""Reusable bank2ai MCP tool specification.

This package isolates the bank2ai tool spec, names, descriptions, input
parameter signatures, and Pydantic response models, so multiple MCP
servers can expose the same surface without duplicating it. Each server
provides async handler callables and calls `register_tools(app, ...)`.

By default, output schemas are inferred by FastMCP from the Pydantic
response-model annotations on the registered tool functions. Servers
can opt into progressive disclosure (lean `list_tools` payloads, full
output schemas fetched on demand via a `describe-tools` meta tool) by
passing ``output_schemas="discovery"`` to ``register_tools``.

Tool registrations are split by domain across the submodules of this
package; `register_tools` is the supported entry point.
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp import FastMCP
from pydantic import Field

from .accounts import register_get_accounts
from .base import (
    TOOL_RESPONSE_MODELS,
    Handler,
    OutputSchemaMode,
)
from .recipients import register_create_recipient, register_get_recipients
from .transactions import (
    register_get_categories,
    register_get_transaction,
    register_get_transactions,
    register_get_transactions_summary,
)
from .transfers import register_execute_transfer, register_prepare_transfer


__all__ = [
    "Handler",
    "OutputSchemaMode",
    "register_tools",
]


def register_tools(
    app: FastMCP,
    *,
    get_accounts: Optional[Handler] = None,
    get_transactions: Optional[Handler] = None,
    get_transaction: Optional[Handler] = None,
    get_categories: Optional[Handler] = None,
    get_transactions_summary: Optional[Handler] = None,
    get_recipients: Optional[Handler] = None,
    create_recipient: Optional[Handler] = None,
    prepare_transfer: Optional[Handler] = None,
    execute_transfer: Optional[Handler] = None,
    output_schemas: OutputSchemaMode = "inline",
) -> None:
    """Register bank2ai MCP tools on `app`, dispatching to the handlers
    that were passed in. Tools whose handler is omitted are not
    registered, allowing servers to expose only a subset of the spec.

    Each handler is invoked with keyword arguments matching the tool's
    input schema (using the snake_case names declared below). Handlers
    may return either dicts shaped like the response model or model
    instances directly, FastMCP serializes both via Pydantic.

    ``output_schemas`` controls how output JSON Schemas are exposed:

    * ``"inline"`` (default): FastMCP inlines each tool's output schema
      in ``list_tools``, inferred from its Pydantic return annotation.
    * ``"discovery"``: ``list_tools`` returns no output schemas. A
      companion ``describe-tools`` tool is registered so clients can
      pull the schemas they need on demand (progressive disclosure).
    * ``"off"``: output schemas are suppressed and no meta tool is
      registered. Use when clients have the schemas out of band.
    """

    registered: list[str] = []

    if get_accounts is not None:
        registered.append(
            register_get_accounts(app, get_accounts, output_schemas=output_schemas)
        )
    if get_transactions is not None:
        registered.append(
            register_get_transactions(
                app, get_transactions, output_schemas=output_schemas
            )
        )
    if get_transaction is not None:
        registered.append(
            register_get_transaction(
                app, get_transaction, output_schemas=output_schemas
            )
        )
    if get_categories is not None:
        registered.append(
            register_get_categories(
                app, get_categories, output_schemas=output_schemas
            )
        )
    if get_transactions_summary is not None:
        registered.append(
            register_get_transactions_summary(
                app, get_transactions_summary, output_schemas=output_schemas
            )
        )
    if get_recipients is not None:
        registered.append(
            register_get_recipients(
                app, get_recipients, output_schemas=output_schemas
            )
        )
    if create_recipient is not None:
        registered.append(
            register_create_recipient(
                app, create_recipient, output_schemas=output_schemas
            )
        )
    if prepare_transfer is not None:
        registered.append(
            register_prepare_transfer(
                app, prepare_transfer, output_schemas=output_schemas
            )
        )
    if execute_transfer is not None:
        registered.append(
            register_execute_transfer(
                app, execute_transfer, output_schemas=output_schemas
            )
        )

    if output_schemas == "discovery":
        _register_describe_tools(app, registered)


def _register_describe_tools(
    app: FastMCP,
    registered_names: list[str],
) -> None:
    """Register the `describe-tools` companion that serves output schemas
    on demand. `registered_names` is read at call time so it can be
    populated before this function runs but is captured by reference.
    """

    @app.tool(
        name="describe-tools",
        description=(
            "Return the output JSON Schema for one or more bank2ai "
            "tools registered on this server. Use this when you need "
            "to validate or parse a tool's response: the server omits "
            "`outputSchema` from `tools/list` to keep the listing "
            "compact, and serves the schemas here on demand. Pass "
            "`tool_names` to fetch a subset, or omit it for every "
            "registered tool. Unknown names yield an `outputSchema` "
            "of `null` rather than an error."
        ),
        output_schema=None,
    )
    async def _describe_tools(
        tool_names: Optional[list[str]] = Field(
            default=None,
            description=(
                "Tool names to describe (e.g. `[\"get-accounts\", "
                "\"prepare-transfer\"]`). Omit to receive every "
                "bank2ai tool registered on this server."
            ),
        ),
    ) -> dict[str, Any]:
        target = tool_names if tool_names else list(registered_names)
        schemas: dict[str, dict[str, Any]] = {}
        for name in target:
            if name in registered_names:
                model = TOOL_RESPONSE_MODELS.get(name)
                schemas[name] = {
                    "outputSchema": (
                        model.model_json_schema() if model is not None else None
                    ),
                }
            else:
                schemas[name] = {"outputSchema": None}
        return {"schemas": schemas}
