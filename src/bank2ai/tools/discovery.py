"""Registration for the `describe-tools` meta tool used in discovery mode."""

from __future__ import annotations

from typing import Any, Optional

from fastmcp import FastMCP
from pydantic import Field

from .base import TOOL_RESPONSE_MODELS


def register_describe_tools(
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
