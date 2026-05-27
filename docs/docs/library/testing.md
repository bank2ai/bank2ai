---
title: Testing your server
sidebar_position: 5
description: Drift tests, handler unit tests, and conformance.
---

# Testing your server

Three layers of tests we recommend.

## 1. Spec drift test

Verify your server registers the full bank2ai tool surface. The reference test pattern (used by [`bank2ai-demo`](https://github.com/bank2ai/bank2ai/blob/main/examples/demo/tests/test_schema_sync.py)):

```python
import json
from pathlib import Path

from bank2ai_demo.server import app

SPEC_FILE = Path(__file__).parents[3] / "specs" / "bank2ai.json"

async def test_server_matches_spec():
    spec = json.loads(SPEC_FILE.read_text())
    expected_tools = {t["name"] for t in spec["tools"]}
    registered = {t.name for t in await app.list_tools()}
    assert expected_tools <= registered, f"missing tools: {expected_tools - registered}"
```

Run it in CI. If you upgrade `bank2ai`, this catches a missing tool registration immediately.

## 2. Handler unit tests

Unit-test the mappers between your backend shape and the bank2ai shape. These are the components most likely to drift when your bank's API changes.

```python
def test_account_mapper_marks_credit_cards_non_withdrawal():
    row = AcmeAccountRow(id="x", kind="credit", balance=-100, ...)
    out = _to_bank2ai_account(row)
    assert out.accountType == "Credit"
    assert out.isWithdrawalAccount is False
```

## 3. End-to-end client smoke test

Spin up the server in a subprocess (or in-process via FastMCP's test helpers) and have a client call each tool. The reference [demo client](https://github.com/bank2ai/bank2ai/blob/main/examples/demo/src/bank2ai_demo/client.py) shows a workable pattern.

End-to-end tests are how you catch things like "I forgot to wire up `execute-transfer`". The drift test catches missing *registrations*; an end-to-end test catches missing *behavior*.

## Don't test what you don't own

- The library's tool schemas come from `bank2ai`. If you find yourself writing a test for "the `get-accounts` input schema has the right fields", you're testing the wrong layer, that's the library's job.
- The protocol layer is FastMCP's responsibility. Trust it; don't write tests that re-implement schema validation.
