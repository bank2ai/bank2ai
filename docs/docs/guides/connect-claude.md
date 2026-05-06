---
title: Connect from Claude
sidebar_position: 2
description: Point Claude Desktop or Claude Code at a bank2ai server.
---

# Connect from Claude

Bank2ai servers speak MCP, so any MCP-aware client can use them. Below are the minimal configurations for the two most common Claude clients.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on your platform:

```json
{
  "mcpServers": {
    "bank2ai-demo": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/bank2ai/examples/demo",
        "run", "bank2ai-demo"
      ]
    }
  }
}
```

Restart Claude Desktop. The eight bank2ai tools should appear in the tool picker — try asking *"What did I spend on groceries last month?"*.

## Claude Code

Add the server to your Claude Code MCP config (project- or user-scoped, see [Claude Code docs](https://docs.claude.com/en/docs/claude-code/mcp)):

```json
{
  "mcpServers": {
    "bank2ai-demo": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/bank2ai/examples/demo",
        "run", "bank2ai-demo"
      ]
    }
  }
}
```

## Connecting to a real bank server

Same config, different command — point at whatever entry point your server exposes:

```json
{
  "mcpServers": {
    "bank2ai-yourbank": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/bank2ai/examples/yourbank",
        "run", "bank2ai-yourbank"
      ],
      "env": {
        "BANK2AI_YOURBANK_BASE_URL": "https://api.yourbank.example/v1"
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
