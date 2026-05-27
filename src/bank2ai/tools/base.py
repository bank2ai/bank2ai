"""Handler protocol, output-schema modes, and shared decorator helpers."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel

from ..models import (
    AccountList,
    CategoryList,
    CreateRecipientResponse,
    ExecuteTransferResponse,
    GetTransactionResponse,
    PrepareTransferResponse,
    RecipientList,
    TransactionList,
    TransactionsSummary,
)


# Handlers are async callables receiving the input-schema's keyword args
# and returning JSON-serializable data shaped like the response model.
Handler = Callable[..., Awaitable[Any]]

OutputSchemaMode = Literal["inline", "discovery", "off"]


# Canonical response model for each bank2ai tool. Used both as the
# return-type annotation that FastMCP introspects in `inline` mode and
# as the source of schemas served by `describe-tools` in `discovery`
# mode, so the two paths cannot diverge.
TOOL_RESPONSE_MODELS: dict[str, type[BaseModel]] = {
    "get-accounts": AccountList,
    "get-transactions": TransactionList,
    "get-transaction": GetTransactionResponse,
    "get-categories": CategoryList,
    "get-transactions-summary": TransactionsSummary,
    "get-recipients": RecipientList,
    "create-recipient": CreateRecipientResponse,
    "prepare-transfer": PrepareTransferResponse,
    "execute-transfer": ExecuteTransferResponse,
}


def build_decorator_helpers(
    output_schemas: OutputSchemaMode,
) -> tuple[dict[str, Any], Callable[[str], str]]:
    """Return `(out_kwarg, desc_fn)` shared by every tool registration.

    `out_kwarg` is spread into `@app.tool(...)`: empty in `inline` mode so
    FastMCP infers the schema from the response-model annotation, or
    `{"output_schema": None}` to suppress it. `desc_fn` appends the
    discovery-suffix to each tool description when running in
    `discovery` mode.
    """
    out_kwarg: dict[str, Any] = (
        {} if output_schemas == "inline" else {"output_schema": None}
    )
    discovery_suffix = (
        " Output JSON Schema available on demand via `describe-tools`."
        if output_schemas == "discovery"
        else ""
    )

    def desc(text: str) -> str:
        return text + discovery_suffix

    return out_kwarg, desc
