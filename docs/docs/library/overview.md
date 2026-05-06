---
title: Overview
sidebar_position: 1
description: The bank2ai Python package — what's in it and when to use it.
---

# The `bank2ai` Python library

`bank2ai` is the **reference implementation** of the [Bank2AI specification](/docs/specification/overview). It exists to make the easiest path to a compliant server also the safest one.

## What's in the box

```python
from bank2ai import (
    # Models
    Account, Transaction, Category, Recipient,
    SpendingSummary, TransferPreparedResponse, ExecuteTransferResponse,
    CreateRecipientResponse,
    # MCP wiring
    register_tools, Handler,
)
```

| Module | Responsibility |
| --- | --- |
| [`bank2ai.models`](./models) | Pydantic models for every Bank2AI input/output shape. |
| [`bank2ai.tools`](./register-tools) | `register_tools(app, ...)` — wires Bank2AI tools onto a [FastMCP](https://github.com/jlowin/fastmcp) app. Pass handlers for the subset of the surface you implement. |

That's it. There's no auth layer, no HTTP client, no framework lock-in. The library does one job: it makes sure your server speaks the spec correctly.

## When to use it

| Scenario | Use the library? |
| --- | --- |
| Building a Bank2AI server in Python | **Yes** — start here. |
| Building a server in another language | No — implement against [`specs/bank2ai.json`](https://github.com/bank2ai/bank2ai/blob/main/specs/bank2ai.json) directly. |
| Building a Bank2AI client | No — clients use the MCP `tools/list` response from each server. The schemas in `bank2ai.json` are useful for code generation. |
| Building agent skills on top | No — skills consume tool calls; they don't import this library. |

## Design principles

- **Schemas are fixed by the spec.** The library does not let you rename a tool, change a field name, or alter a type.
- **Authentication is your problem.** The library does not provide one. See [Authentication](/docs/specification/overview#4-authentication) for patterns.
- **Handlers, not classes.** You provide async callables for the tools you want to expose; the library wires them up. No subclassing required, and every handler is optional.
- **Pydantic in, Pydantic out.** Handlers may return either `dict`s shaped like the response model or model instances directly — FastMCP serializes both.

## Next

- [`register_tools` reference](./register-tools) — the surface in detail.
- [Models reference](./models) — every input/output shape.
- [Writing handlers](./writing-handlers) — patterns for plugging into a real backend.
- [Testing your server](./testing) — drift tests and conformance.
