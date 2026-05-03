# bank2ai-demo

Reference MCP server built on [`bank2ai`](../..) and backed by hardcoded data in `data.py`. Run it locally to develop or test AI agents without a real bank.

## Run

```bash
# from the repo root
uv sync
uv run --package bank2ai-demo bank2ai-demo
```

Or invoke the module directly:

```bash
uv run --package bank2ai-demo python -m bank2ai_demo
```

## Try it with the demo client

In another terminal:

```bash
uv run --package bank2ai-demo python -m bank2ai_demo.client
```

The client lists tools, fetches accounts/transactions/categories, runs a spending summary, searches recipients, and prepares a transfer (without executing).

## Customising the test data

Edit `src/bank2ai_demo/data.py` — `ACCOUNTS`, `TRANSACTIONS`, `CATEGORIES`, `RECIPIENTS`, and the `generate_transactions()` helper.

## Use with Claude Desktop

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

## Tests

```bash
uv run --package bank2ai-demo pytest
```

`test_schema_sync.py` verifies that the demo server registers the full Bank2AI tool surface defined by the `bank2ai` library.
