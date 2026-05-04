---
title: Installation
sidebar_position: 2
description: Install the bank2ai Python library.
---

# Installation

Bank2AI's reference implementation is a Python package. It requires **Python 3.11+**.

## With pip

```bash
pip install bank2ai
```

## With uv

```bash
uv add bank2ai
```

## Verify

```bash
python -c "import bank2ai; print(bank2ai.__name__)"
```

That's it. To stand up a server, continue with the [Quickstart](./quickstart). To run the demo server straight from a clone of the repo without installing anything globally, see [Run the demo](/docs/guides/run-the-demo).

## What's in the package

| Module | Contents |
| --- | --- |
| `bank2ai.models` | Pydantic data models for the shared banking vocabulary — `Account`, `Transaction`, `Recipient`, `Category`, plus the request/response shapes for transfers and spending summaries. |
| `bank2ai.tools` | Reusable MCP tool surface — `register_tools` wires the eight Bank2AI tools onto a [FastMCP](https://github.com/jlowin/fastmcp) app and dispatches each call to handlers you provide. |

Authentication is intentionally **outside** this library. See [Specification → Authentication](/docs/specification/overview#4-authentication) for the rationale and patterns.
