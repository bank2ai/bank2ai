---
title: Overview
sidebar_position: 1
description: The bank2ai marketplace, a registry of compliant servers and the agent skills built on top.
---

# The bank2ai marketplace

A spec is only as useful as the surface area it covers. The **bank2ai marketplace** is a registry of:

- **MCP servers** that implement the bank2ai tool surface for a specific bank or fintech, and
- **agent skills** built on top of that surface (budgeting helpers, transfer assistants, statement explainers, …).

Entries are packaged as [Claude Code plugins](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces), so installing a bank or skill is a single command for Claude Code users, and any other client that speaks the same plugin format can consume the registry too.

## Why a marketplace?

Bank2ai's value compounds with adoption. A budgeting skill written today should keep working tomorrow when a new bank publishes its server, with zero changes from the skill author. The marketplace is the contract that makes that possible: every entry implements the same eight-tool surface, so skills depend on *tool names*, never on *server identity*.

## What's in it

| Type | Examples |
| --- | --- |
| **Bank servers** | One per bank or fintech, `bank2ai-acme`, `bank2ai-yourbank`, … |
| **Skills** | Domain-specific agent skills, budgeting helpers, statement explainers, transfer assistants, subscription auditors, cash-flow forecasters. |

## How to participate

- **Use it.** [Install a server or skill](./installing) in Claude Code with one command.
- **Publish a server.** If you've built a bank2ai server for a bank, [publish it](./publishing-a-server) so others can install it.
- **Publish a skill.** If you've built an agent skill on top of bank2ai, [publish it](./publishing-a-skill).

## Where it lives

The marketplace registry is hosted at [github.com/bank2ai/marketplace](https://github.com/bank2ai/marketplace) and discoverable from any Claude Code client speaking the plugin marketplace format.
