---
title: Publishing a server
sidebar_position: 2
description: How to publish a Bank2AI MCP server to the marketplace.
---

# Publishing a server

Got a working Bank2AI server for a bank or fintech? Here's how to ship it through the marketplace so any Claude Code user can install it.

## Prerequisites

- Your server registers all eight tools defined by the [spec](/docs/specification/overview). Run the [drift test](/docs/library/testing#1-spec-drift-test) — it should pass.
- Your server has a stable entry point — a CLI or `python -m` invocation, ideally a single command.
- A short README explaining what the server is for, who it's for, and how authentication works.

## Package as a Claude Code plugin

Follow the [Claude Code plugin format](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces). At minimum your plugin needs:

```
bank2ai-yourbank/
├── plugin.json          # plugin manifest
└── server/              # your server's source or installer
```

Example `plugin.json`:

```json
{
  "name": "bank2ai-yourbank",
  "version": "0.1.0",
  "description": "Bank2AI MCP server for Acme Bank",
  "type": "mcp-server",
  "implements": ["bank2ai/0.1"],
  "command": "uv",
  "args": ["run", "bank2ai-yourbank"],
  "homepage": "https://github.com/your-org/bank2ai-yourbank"
}
```

The `implements` field tells the registry which Bank2AI version your server speaks; this is what lets skills declare compatibility.

## Submit to the registry

1. Fork [`bank2ai/marketplace`](https://github.com/bank2ai/marketplace).
2. Add an entry pointing at your published plugin.
3. Open a pull request. CI re-runs your drift test and validates `plugin.json`.

Once merged, your server is discoverable as `bank2ai/yourbank` and installable via `/plugin install bank2ai/yourbank`.

## What we look for in a review

- **Spec compliance.** Drift test passes.
- **Honest scope.** The README clearly states which markets, account types, and currencies are supported.
- **Sensible authentication.** No hardcoded credentials shipped in the plugin; documented setup for users.
- **Maintainership.** A maintainer named in the manifest who can be reached when something breaks.
