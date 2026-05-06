---
title: Run the demo server
sidebar_position: 1
description: Stand up the bank2ai demo server backed by hardcoded data.
---

# Run the demo server

`bank2ai-demo` is a reference MCP server backed by hardcoded data — useful for developing or testing AI clients against the full bank2ai surface without a real bank in the loop.

## Clone the repo

```bash
git clone https://github.com/bank2ai/bank2ai
cd bank2ai
uv sync
```

## Run

```bash
uv run --package bank2ai-demo bank2ai-demo
```

Or directly as a module:

```bash
uv run --package bank2ai-demo python -m bank2ai_demo
```

## Try it from the demo client

In another terminal:

```bash
uv run --package bank2ai-demo python -m bank2ai_demo.client
```

The client lists tools, fetches accounts/transactions/categories, runs a spending summary, searches recipients, and prepares a transfer (without executing).

## Customise the data

Edit `examples/demo/src/bank2ai_demo/data.py` — `ACCOUNTS`, `TRANSACTIONS`, `CATEGORIES`, `RECIPIENTS`, and the `generate_transactions()` helper.

## Use it from Claude Desktop / Claude Code

Drop this into your client's MCP config:

```json
{
  "mcpServers": {
    "bank2ai-demo": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/bank2ai/examples/demo",
        "run", "bank2ai-demo"
      ]
    }
  }
}
```

See [Connect from Claude](./connect-claude) for screenshots and step-by-step instructions.

## Run the tests

```bash
uv run --package bank2ai-demo pytest
```

`test_schema_sync.py` verifies the demo server registers the full bank2ai tool surface defined by the `bank2ai` library.
