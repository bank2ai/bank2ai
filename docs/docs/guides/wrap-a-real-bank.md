---
title: Wrap a real bank
sidebar_position: 3
description: How to wire the bank2ai surface to a real bank backend.
---

# Wrap a real bank

This guide walks through the patterns for wiring a real bank backend behind the shared `bank2ai` tool surface — including how to handle the most common authentication pattern (credentials → bearer token).

## Configure

Most banks expose a base URL and require some form of credentials. A typical env layout:

| Variable | Required | Description |
| --- | --- | --- |
| `BANK2AI_<BANK>_BASE_URL` | yes | API base URL for the bank backend. |
| `BANK2AI_<BANK>_EMAIL` | no | Default credential email (otherwise prompted via MCP elicitation). |
| `BANK2AI_<BANK>_PASSWORD` | no | Default credential password. |
| `BANK2AI_<BANK>_CULTURE` | no | Locale, e.g. `en-GB`. |

Adjust the variable names for your bank, and copy `.env.example` → `.env` before running.

## Run

```bash
uv run --package bank2ai-<your-bank> bank2ai-<your-bank>
```

## How authentication works

A typical bank2ai server supports three credential paths, in order of preference:

1. **Inbound MCP `access_token`.** If the MCP client forwards a bearer token issued by the bank's identity provider, the server uses it directly. Best for clients that have already authenticated.
2. **Server-configured email + password.** If credential env vars are set, the server exchanges them for a bearer token at startup and refreshes as needed.
3. **MCP elicitation.** If the client supports elicitation, the server prompts the end user interactively for `email` / `password`. Otherwise it exposes a dynamic `authenticate` tool that the LLM can call once with credentials.

This three-way fallback is a useful template — most real banks need at least options 1 and 2.

## How handlers map onto a bank API

Each bank2ai tool is implemented as a thin async handler that calls the bank API and maps the response into the bank2ai shape. The handler does the work the spec defines; the mapper does the work your backend shape forces.

```python
async def get_accounts(*, only_withdrawal_accounts, account_type):
    rows = await bank_client.list_accounts()
    if only_withdrawal_accounts:
        rows = [r for r in rows if r["IsActive"] and r["IsAvailable"]]
    if account_type:
        rows = [r for r in rows if r["AccountTypeName"] == account_type]
    return [_to_bank2ai_account(r) for r in rows]
```

For a working reference implementation, see the example servers in the [`examples/`](https://github.com/bank2ai/bank2ai/tree/main/examples) directory.

## What to copy when wrapping your own bank

1. **Project layout.** `pyproject.toml`, `src/<your_pkg>/server.py`, `src/<your_pkg>/__main__.py`. Mirror an existing reference server.
2. **Credential handling.** Whichever of the three patterns above fits your backend.
3. **Mappers.** One per bank2ai shape — `_to_bank2ai_account`, `_to_bank2ai_transaction`, etc. Unit-test these.
4. **The two-step transfer flow.** Cache the prepared transfer keyed by `(withdrawal_account_id, recipient_account_number, amount)` and reject `execute_transfer` calls without a matching preparation. See [Writing handlers → prepare → execute](/docs/library/writing-handlers#pattern-prepare--execute-for-transfers).

Then run the [drift test](/docs/library/testing#1-spec-drift-test) and you're compliant.
