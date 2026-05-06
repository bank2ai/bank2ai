# bank2ai-meniga

Reference bank2ai MCP server backed by [Meniga](https://meniga.com) APIs. Demonstrates wiring a real bank backend behind the bank2ai tool surface, including credential-based authentication.

📖 Full walkthrough: [bank2ai.com/docs/guides/wrap-a-real-bank](https://bank2ai.com/docs/guides/wrap-a-real-bank)

## Configure

```bash
cp .env.example .env
# edit .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `BANK2AI_MENIGA_BASE_URL` | yes | API base URL, e.g. `https://api.meniga.cloud/user/core` |
| `BANK2AI_MENIGA_EMAIL` | no | Default credential email (otherwise prompted via MCP elicitation). |
| `BANK2AI_MENIGA_PASSWORD` | no | Default credential password. |
| `BANK2AI_MENIGA_CULTURE` | no | Locale, defaults to `en-GB`. |

## Run

```bash
# from the repo root
uv sync
uv run --package bank2ai-meniga bank2ai-meniga
```
