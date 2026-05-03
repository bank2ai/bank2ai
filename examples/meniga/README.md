# bank2ai-meniga

Bank2AI MCP server backed by [Meniga](https://meniga.com) APIs (e.g. `api.meniga.cloud`). Demonstrates how to wire a real bank backend behind the shared `bank2ai` tool surface, including the optional credential-based auth flow.

## Configure

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable                  | Required | Description                                               |
| ------------------------- | -------- | --------------------------------------------------------- |
| `BANK2AI_MENIGA_BASE_URL` | yes      | API base URL, e.g. `https://api.meniga.cloud/user/core`   |
| `BANK2AI_MENIGA_EMAIL`    | no       | Default credential email (otherwise prompted via MCP elicitation) |
| `BANK2AI_MENIGA_PASSWORD` | no       | Default credential password                               |
| `BANK2AI_MENIGA_CULTURE`  | no       | Locale, defaults to `en-GB`                               |
| `BANK2AI_LOG_RESPONSES`   | no       | Set to `1`/`true` to log full tool responses              |

## Run

```bash
# from the repo root
uv sync
uv run --package bank2ai-meniga bank2ai-meniga
```

Or invoke the module directly:

```bash
uv run --package bank2ai-meniga python -m bank2ai_meniga
```

## Use with Claude Desktop

```json
{
  "mcpServers": {
    "bank2ai-meniga": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/bank2ai/examples/meniga",
        "run", "bank2ai-meniga"
      ],
      "env": {
        "BANK2AI_MENIGA_BASE_URL": "https://api.meniga.cloud/user/core"
      }
    }
  }
}
```

When the MCP client supports elicitation, the server prompts the end user for `email`/`password` interactively. Otherwise it exposes a dynamic `authenticate` tool that the LLM can call once with credentials.
