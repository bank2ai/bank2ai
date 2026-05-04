# bank2ai

A Python library and language-neutral specification that help banks expose their services to AI agents over the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). With a Bank2AI-compliant MCP server, an AI client (or, through it, an end customer) can read accounts and transactions, look up recipients, run spending summaries, and prepare/execute transfers — using the same tool surface across every bank.

The repo contains:

* the **`bank2ai` Python library** (this directory's `src/bank2ai/`) — handlers, response models, and auth helpers built on top of [FastMCP](https://github.com/jlowin/fastmcp);
* the **language-neutral spec** (`specs/`) — JSON Schemas + a narrative document — so the same surface can be reimplemented in any language;
* **example MCP servers** (`examples/`) backed by demo data and by the Meniga API; and
* **docs** (`docs/`) — a Docusaurus site, planned for [bank2ai.com](https://bank2ai.com).

## Quick start

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


## What's in the package

| Module           | Contents                                                  |
| ---------------- | --------------------------------------------------------- |
| `bank2ai.models` | Pydantic data models: `Account`, `Transaction`, `Recipient`, `Category`, `AuthParam`, `AuthResponse`, … |
| `bank2ai.mcp`    | Tool surface (`register_tools`), response models, auth middleware, dynamic `authenticate` tool |

## Specification

The Bank2AI tool surface is specified independently of any single implementation under [`specs/`](./specs):

* [`specs/bank2ai.spec.md`](./specs/bank2ai.spec.md) — narrative spec (overview, lifecycle, per-tool semantics, auth protocol).
* [`specs/bank2ai.json`](./specs/bank2ai.json) — machine-readable: tool list with full input/output JSON Schemas plus shared model schemas.

The Python package in this repo is the reference implementation; alternative implementations in other languages are welcome and should track the spec.

## Repo layout

```
.
├── src/bank2ai/        # the library (PyPI: bank2ai)
├── examples/
│   ├── demo/           # MCP server backed by hardcoded data
│   └── meniga/         # MCP server backed by Meniga APIs
├── specs/              # language-neutral spec
├── docs/               # Docusaurus site for bank2ai.com (planned)
├── scripts/            # repo automation (e.g. spec regeneration)
├── pyproject.toml      # uv workspace root + bank2ai library
└── LICENSE
```

## Working in the monorepo

This repo is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/). From the root:

```bash
uv sync                                       # install library + examples + dev deps
uv run --package bank2ai-demo bank2ai-demo    # run the demo server
uv run pytest examples/demo                   # run the demo example tests
uv run python scripts/generate_spec.py        # regenerate specs/bank2ai.json
```

Each example also has its own README with run/test instructions.

## Adding a new bank

Copy `examples/demo` (or `examples/meniga` if you need authentication), rename the package, update `pyproject.toml`, and replace the handlers in `server.py` with calls into your bank's APIs. Because `register_tools` lives in `bank2ai`, you don't need to redefine schemas — just plug in handlers.

## License

MIT — see [LICENSE](./LICENSE).
