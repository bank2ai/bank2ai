---
title: Installing servers and skills
sidebar_position: 4
description: How end users install bank2ai servers and skills from the marketplace.
---

# Installing from the marketplace

The marketplace is consumable from any Claude Code client speaking the [plugin marketplace format](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces).

## Add the marketplace

Once, in Claude Code:

```
/plugin marketplace add bank2ai/marketplace
```

This subscribes Claude Code to the registry; new entries appear automatically.

## Install a server

```
/plugin install bank2ai/yourbank
```

Claude Code installs the plugin, wires the MCP server into your session, and prompts for any required configuration (e.g. credentials, API base URL). The bank2ai tools then appear in your tool picker.

## Install a skill

```
/plugin install bank2ai/budgeting-helper
```

If the skill `requires` tools your currently installed server doesn't register, Claude Code warns you up front instead of failing mid-conversation.

## Uninstall

```
/plugin uninstall bank2ai/yourbank
```

## Other clients

Any client speaking the same plugin marketplace format can consume the registry. The exact slash command may differ; consult your client's documentation.
