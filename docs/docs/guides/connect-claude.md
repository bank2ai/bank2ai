---
title: Connect from Claude
sidebar_position: 2
description: Point Claude Desktop or Claude Code at a Bank2AI server.
---

# Connect from Claude

Bank2AI servers speak MCP, so any MCP-aware client can use them. Below are the minimal configurations for the two most common Claude clients.

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

Restart Claude Desktop. The eight Bank2AI tools should appear in the tool picker — try asking *"What did I spend on groceries last month?"*.

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

Same config, different command — point at whatever entry point your server exposes. For the Meniga reference:

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

See the [Meniga walkthrough](./wrap-a-real-bank) for credential handling.

## Installing from the marketplace

When a Bank2AI server is published to the [marketplace](/docs/marketplace/overview), Claude Code users install it with one command:

```
/plugin install bank2ai/<server-name>
```

No JSON editing required. See [Marketplace → Installing](/docs/marketplace/installing).
