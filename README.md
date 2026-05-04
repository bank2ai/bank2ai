# bank2ai

**Bank2AI connects digital banking data and operations with AI agents.**

The language of banking is universal — accounts, transactions, transfers, bill payments, recipients, loans, savings — and Bank2AI codifies that language as an open standard so banks and fintechs can collaborate on AI tools and skills instead of each rebuilding the same surface. Once a bank speaks Bank2AI over the [Model Context Protocol (MCP)](https://modelcontextprotocol.io), any compliant AI client can read accounts and transactions, look up recipients, run spending summaries, and prepare/execute transfers — using the same vocabulary across every bank.

Bank2AI is also an ecosystem. The Bank2AI **marketplace** is a registry of MCP servers and agent skills that implement this standard, distributed as a [Claude Code marketplace](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces) so any Claude Code user can install a bank or skill with one command (and any other client speaking the same plugin format can do the same).

The repo contains:

* the **`bank2ai` Python library** (`src/bank2ai/`) — shared data models and a reusable MCP tool surface (`register_tools`) built on top of [FastMCP](https://github.com/jlowin/fastmcp);
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
| `bank2ai.models` | Pydantic data models for the shared banking vocabulary: `Account`, `Transaction`, `Recipient`, `Category`, plus the request/response shapes for transfers and spending summaries. |
| `bank2ai.mcp`    | Reusable MCP tool surface — `register_tools` wires the eight Bank2AI tools onto a FastMCP app and dispatches each call to handlers you provide. |

Authentication is intentionally outside this library: each server obtains credentials however suits its backend (inbound MCP `access_token`, server-configured API credentials, OAuth, etc.). See [§4 of the spec](./specs/bank2ai.spec.md#4-authentication).

## Specification

The Bank2AI tool surface is specified independently of any single implementation under [`specs/`](./specs):

* [`specs/bank2ai.spec.md`](./specs/bank2ai.spec.md) — narrative spec (overview, lifecycle, per-tool semantics, error model).
* [`specs/bank2ai.json`](./specs/bank2ai.json) — machine-readable: tool list with full input/output JSON Schemas plus shared model schemas.

The Python package in this repo is the reference implementation; alternative implementations in other languages are welcome and should track the spec.

## Marketplace

Bank2AI is more than a contract — it's an ecosystem. The Bank2AI marketplace is a registry of:

* **MCP servers** that implement the Bank2AI tool surface for a specific bank or fintech, and
* **agent skills** built on top of that surface (budgeting helpers, transfer assistants, statement explainers, …).

Entries are packaged as [Claude Code plugins](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces), so installing a bank or skill is a single `/plugin install` away for Claude Code users — and any other client that speaks the same plugin format can consume the registry too.

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
