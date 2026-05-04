---
title: Wrap a real bank (Meniga walkthrough)
sidebar_position: 3
description: How the Meniga reference server wires the Bank2AI surface to a real bank API.
---

# Wrap a real bank: the Meniga walkthrough

`bank2ai-meniga` is a reference MCP server backed by [Meniga](https://meniga.com) APIs (e.g. `api.meniga.cloud`). It demonstrates how to wire a real bank backend behind the shared `bank2ai` tool surface — and how to handle the most common authentication pattern (credentials → bearer token).

## Configure

Copy the env template and fill in values:

```bash
cd examples/meniga
cp .env.example .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `BANK2AI_MENIGA_BASE_URL` | yes | API base URL, e.g. `https://api.meniga.cloud/user/core` |
| `BANK2AI_MENIGA_EMAIL` | no | Default credential email (otherwise prompted via MCP elicitation). |
| `BANK2AI_MENIGA_PASSWORD` | no | Default credential password. |
| `BANK2AI_MENIGA_CULTURE` | no | Locale, defaults to `en-GB`. |

## Run

```bash
uv run --package bank2ai-meniga bank2ai-meniga
```

## How authentication works

The Meniga server supports three credential paths, in order of preference:

1. **Inbound MCP `access_token`.** If the MCP client forwards a Meniga bearer token, the server uses it directly. Best for clients that have already authenticated against Meniga's identity provider.
2. **Server-configured email + password.** If `BANK2AI_MENIGA_EMAIL` and `BANK2AI_MENIGA_PASSWORD` are set, the server exchanges them for a Meniga bearer token at startup and refreshes as needed.
3. **MCP elicitation.** If the client supports elicitation, the server prompts the end user interactively for `email` / `password`. Otherwise it exposes a dynamic `authenticate` tool that the LLM can call once with credentials.

This three-way fallback is a useful template — most real banks need at least options 1 and 2.

## How handlers map onto the Meniga API

Each Bank2AI tool is implemented as a thin async handler that calls the Meniga API and maps the response into the Bank2AI shape. The handler does the work the spec defines; the mapper does the work your backend shape forces.

```python
async def get_accounts(*, only_withdrawal_accounts, account_type):
    rows = await meniga_client.list_accounts()
    if only_withdrawal_accounts:
        rows = [r for r in rows if r["IsActive"] and r["IsAvailable"]]
    if account_type:
        rows = [r for r in rows if r["AccountTypeName"] == account_type]
    return [_to_bank2ai_account(r) for r in rows]
```

Read the full implementation in [`examples/meniga/src/bank2ai_meniga/server.py`](https://github.com/bank2ai/bank2ai/blob/main/examples/meniga/src/bank2ai_meniga/server.py).

## What to copy when wrapping your own bank

1. **Project layout.** `pyproject.toml`, `src/<your_pkg>/server.py`, `src/<your_pkg>/__main__.py`. Mirror the Meniga example.
2. **Credential handling.** Whichever of the three patterns above fits your backend.
3. **Mappers.** One per Bank2AI shape — `_to_bank2ai_account`, `_to_bank2ai_transaction`, etc. Unit-test these.
4. **The two-step transfer flow.** Cache the prepared transfer keyed by `(withdrawal_account_id, recipient_account_number, amount)` and reject `execute_transfer` calls without a matching preparation. See [Writing handlers → prepare → execute](/docs/library/writing-handlers#pattern-prepare--execute-for-transfers).

Then run the [drift test](/docs/library/testing#1-spec-drift-test) and you're compliant.
