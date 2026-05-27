---
title: Connect from Claude
sidebar_position: 2
description: Point Claude Desktop or Claude Code at a bank2ai server.
---

# Connect from Claude

## Claude Code

From your project directory:

```bash
claude mcp add my-server -- uv run --directory "$PWD" python server.py
claude
```

Type `/mcp` to confirm the server is connected.

## Claude Desktop

:::info
Claude Desktop is not available on Linux. Linux users should use Claude Code.
:::

Open **Claude Desktop → Settings → Developer → Edit Config** — this opens the correct config file for your install. Add `mcpServers` alongside any existing keys:

**macOS:**

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/your/server", "python", "server.py"]
    }
  }
}
```

**Windows (native):**

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\Users\\YOU\\your-server", "python", "server.py"]
    }
  }
}
```

**Windows + WSL2** (project inside WSL, Desktop on Windows):

```json
{
  "mcpServers": {
    "my-server": {
      "command": "wsl.exe",
      "args": ["--", "bash", "-lc", "cd /home/YOU/your-server && /home/YOU/.local/bin/uv run python server.py"]
    }
  }
}
```

Fully quit Claude Desktop (hamburger menu in the top-left → File → Exit) and reopen it.

:::note
Do not use the **Settings → Connectors** UI for a local stdio server — that UI is for remote HTTP servers only. JSON config is the only way to register a local server.
:::

## Connecting to a real bank server

Same config, different command — point at your server's entry point:

```json
{
  "mcpServers": {
    "my-bank": {
      "command": "uv",
      "args": [
        "run", "--directory", "/path/to/your/bank-server",
        "run", "your-bank-server"
      ],
      "env": {
        "BANK_API_BASE_URL": "https://api.yourbank.example/v1"
      }
    }
  }
}
```

See the [real-bank guide](./wrap-a-real-bank) for credential handling.

## Installing from the marketplace

When a bank2ai server is published to the [marketplace](/docs/marketplace/overview), Claude Code users install it with one command:

```
/plugin install bank2ai/<server-name>
```

No JSON editing required. See [Marketplace → Installing](/docs/marketplace/installing).
