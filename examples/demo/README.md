# bank2ai-demo

Reference Bank2AI MCP server backed by hardcoded data. Use it to develop or test AI agents without a real bank.

📖 Full guide: [bank2ai.com/docs/guides/run-the-demo](https://bank2ai.com/docs/guides/run-the-demo)

## Run

```bash
# from the repo root
uv sync
uv run --package bank2ai-demo bank2ai-demo
```

## Try it

In another terminal:

```bash
uv run --package bank2ai-demo python -m bank2ai_demo.client
```

## Tests

```bash
uv run --package bank2ai-demo pytest
```
