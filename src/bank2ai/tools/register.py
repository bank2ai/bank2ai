"""The `register_tools` orchestrator that wires per-tool registrations onto an app."""

from __future__ import annotations

from typing import Optional

from fastmcp import FastMCP

from .accounts import register_get_accounts
from .base import Handler, OutputSchemaMode
from .categories import register_get_categories
from .discovery import register_describe_tools
from .recipients import register_create_recipient, register_get_recipients
from .transactions import (
    register_get_transaction,
    register_get_transactions,
    register_get_transactions_summary,
)
from .transfers import register_execute_transfer, register_prepare_transfer


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
        register_describe_tools(app, registered)
