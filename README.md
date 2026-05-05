# Bank2AI

**The open standard for connecting digital banking with AI agents.**

The language of banking is universal — accounts, transactions, transfers, bill payments, recipients, loans, savings — and Bank2AI codifies that language as a [Model Context Protocol](https://modelcontextprotocol.io) tool surface. Once a bank speaks Bank2AI, any compliant AI client can read accounts, look up recipients, run spending summaries, and prepare/execute transfers — using the same vocabulary across every bank.

📖 **Full documentation:** [bank2ai.com](https://bank2ai.com)
📦 **Specification:** [`specs/`](./specs/)
🛒 **Marketplace:** [github.com/bank2ai/marketplace](https://github.com/bank2ai/marketplace)

## Stewarded by Bancony

Bank2AI is freely usable by any bank or fintech. Its development is stewarded by **[Bancony](https://bancony.com)**, which builds enterprise-ready MCP servers, an SDK, an in-channel chat agent (with Generative UI and RAG), and advisory agents on top of the standard. See the [enterprise overview](https://bank2ai.com/docs/enterprise/overview) for details.

## Install

```bash
uv add bank2ai
```

## Quickstart

```python
from fastmcp import FastMCP
from bank2ai import register_tools

app = FastMCP("my-bank")
register_tools(
    app,
    get_accounts=...,
    get_transactions=...,
    get_categories=...,
    get_spending_summary=...,
    search_recipients=...,
    create_recipient=...,
    prepare_transfer=...,
    execute_transfer=...,
)
```

Walk through a full example in the [Quickstart guide](https://bank2ai.com/docs/getting-started/quickstart).

## What's in this repo

| Path | Contents |
| --- | --- |
| [`src/bank2ai/`](./src/bank2ai/) | The Python library (`bank2ai` on PyPI) — Pydantic models + the `register_tools` MCP wiring. |
| [`specs/`](./specs/) | Language-neutral specification — `bank2ai.spec.md` (narrative) and `bank2ai.json` (JSON Schemas). |
| [`examples/demo/`](./examples/demo/) | Reference MCP server backed by hardcoded data. |
| [`examples/meniga/`](./examples/meniga/) | Reference MCP server backed by a real bank API. |
| [`docs/`](./docs/) | Source for [bank2ai.com](https://bank2ai.com). |

## Contributing

Issues and PRs welcome at [github.com/bank2ai/bank2ai](https://github.com/bank2ai/bank2ai). For anything that touches the spec, please open an issue first — see [Contributing](https://bank2ai.com/docs/resources/contributing).

## License

MIT — see [LICENSE](./LICENSE).
