"""Registration for the `get-categories` tool."""

from __future__ import annotations

from fastmcp import FastMCP

from ..models import CategoryList
from .base import Handler, OutputSchemaMode, build_decorator_helpers


def register_get_categories(
    app: FastMCP,
    handler: Handler,
    *,
    output_schemas: OutputSchemaMode,
) -> str:
    out_kwarg, desc = build_decorator_helpers(output_schemas)

    @app.tool(
        name="get-categories",
        description=desc(
            "Get transaction categories. Returns a list of categories "
            "that transactions can be classified into."
        ),
        **out_kwarg,
    )
    async def _get_categories() -> CategoryList:
        return await handler()

    return "get-categories"
