# bank2ai

**The open standard for AI driven banking.**

The language of banking is universal (accounts, transactions, transfers, bill payments, recipients, loans, savings) and bank2ai codifies that language as a [Model Context Protocol](https://modelcontextprotocol.io) tool surface. Once a bank speaks bank2ai, any compliant AI client can read accounts, look up recipients, run spending summaries, and prepare/execute transfers, using the same vocabulary across every bank.

📖 **Full documentation:** [bank2ai.com](https://bank2ai.com)
📦 **Specification:** [`specs/`](./specs/)
🛒 **Marketplace:** [github.com/bank2ai/marketplace](https://github.com/bank2ai/marketplace)

## Stewarded by Bancony

bank2ai is freely usable by any bank or fintech. Its development is stewarded by **[Bancony](https://bancony.com)**, which also builds commercial implementations on top of the standard alongside other vendors and in-house teams. See [Commercial implementations](https://bank2ai.com/docs/enterprise/overview) for the current list.

## Install

```bash
uv add bank2ai
```

## Quickstart

```python
from fastmcp import FastMCP
from bank2ai import register_tools

app = FastMCP("my-bank")

# Every handler is optional, pass only the tools you've implemented.
register_tools(
    app,
    get_accounts=...,
    get_categories=...,
    # get_transactions=..., get_transaction=..., get_transactions_summary=...,
    # get_recipients=..., create_recipient=...,
    # prepare_transfer=..., execute_transfer=...,
)
```

Walk through a full example in the [Quickstart guide](https://bank2ai.com/docs/getting-started/quickstart).

## What's in this repo

| Path | Contents |
| --- | --- |
| [`src/bank2ai/`](./src/bank2ai/) | The Python library (`bank2ai` on PyPI), Pydantic models + the `register_tools` MCP wiring. |
| [`specs/`](./specs/) | Language-neutral specification, `bank2ai.spec.md` (narrative) and `bank2ai.json` (JSON Schemas). |
| [`examples/demo/`](./examples/demo/) | Reference MCP server backed by hardcoded data. |
| [`docs/`](./docs/) | Source for [bank2ai.com](https://bank2ai.com). |


## Contributing

Issues and PRs welcome at [github.com/bank2ai/bank2ai](https://github.com/bank2ai/bank2ai). For anything that touches the spec, please open an issue first, see [Contributing](https://bank2ai.com/docs/resources/contributing).

## License

Apache 2.0, see [LICENSE](./LICENSE).
