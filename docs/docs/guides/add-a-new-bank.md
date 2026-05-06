---
title: Add a new bank
sidebar_position: 4
description: Bootstrap a fresh bank2ai server for a bank that doesn't have one yet.
---

# Add a new bank

The fastest path is to copy [`examples/demo`](https://github.com/bank2ai/bank2ai/tree/main/examples/demo) (or one of the real-bank examples if you need authentication) and replace the handlers.

## 1. Copy a template

```bash
cp -R examples/demo examples/yourbank
cd examples/yourbank
```

## 2. Rename the package

Edit `pyproject.toml`:

```toml
[project]
name = "bank2ai-yourbank"
version = "0.1.0"

[project.scripts]
bank2ai-yourbank = "bank2ai_yourbank:main"
```

Rename the `src/bank2ai_demo/` directory to `src/bank2ai_yourbank/` and update imports.

If you're adding to the bank2ai workspace, register the package in the root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["examples/demo", "examples/yourbank"]

[tool.uv.sources]
bank2ai-yourbank = { workspace = true }
```

## 3. Replace the handlers

In `server.py`, replace the demo handlers with calls into your bank's APIs. You don't need to redefine any schemas — `register_tools` lives in `bank2ai` and is fixed by the spec.

```python
from bank2ai import register_tools
from .acme_client import AcmeBankClient

api = AcmeBankClient(...)

async def get_accounts(*, only_withdrawal_accounts, account_type):
    return await _list_accounts_via_acme(api, only_withdrawal_accounts, account_type)

# … any other handlers you implement …

register_tools(app, get_accounts=get_accounts, ...)
```

Every `register_tools` keyword argument is optional, so you can land tools incrementally — start with `get-accounts` and add the rest as the backend integration matures.

See [Writing handlers](/docs/library/writing-handlers) for patterns and [Wrap a real bank](./wrap-a-real-bank) for a worked example.

## 4. Test it

- Run the [drift test](/docs/library/testing#1-spec-drift-test) so a missing tool registration breaks CI.
- Smoke-test against your real backend with the [demo client](./run-the-demo) pointed at your server.
- [Connect from Claude](./connect-claude) and try a few realistic prompts.

## 5. Publish to the marketplace

Once your server is solid, publish it as a [Claude Code plugin](/docs/marketplace/publishing-a-server) so any client can install it with one command.
