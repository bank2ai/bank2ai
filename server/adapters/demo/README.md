# Demo Adapter

A `BankAdapter` implementation that serves hardcoded test data from `data.py`. Default adapter for the reference server — no external bank required.

## Configure

Set `BANK2AI_ADAPTER=demo` (or omit; demo is the default).

## Sample MCP client config

```json
"bank2ai-demo": {
  "command": "/path/to/bank2ai-server/venv/bin/python",
  "args": ["/path/to/bank2ai-server/server.py"],
  "env": {
    "BANK2AI_LOG_RESPONSES": "true",
    "BANK2AI_LOG_LEVEL": "DEBUG",
    "BANK2AI_ADAPTER": "demo"
  }
}
```

## Test data

See `data.py` for the hardcoded ACCOUNTS, TRANSACTIONS, CATEGORIES, and RECIPIENTS. The `generate_transactions()` helper produces 90 days of realistic activity.
