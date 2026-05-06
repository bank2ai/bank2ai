# bank2ai-demo

Reference bank2ai MCP server backed by hardcoded data. Use it to develop or test AI agents without a real bank.

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

## Inspect
Run this in a terminal
```bash
npx @modelcontextprotocol/inspector
```
In the UI, enter the following:
* Transport: `STDIO`
* Command: `uv`
* Arguments: `--directory /path/to/bank2ai run --package bank2ai-demo bank2ai-demo`

Click **Connect**.