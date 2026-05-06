---
title: Welcome
sidebar_position: 1
description: Bank2AI is the open standard for connecting digital banking with AI agents over MCP.
---

# Welcome to Bank2AI

**Bank2AI is the open standard for connecting digital banking with AI agents.**

The language of banking is universal — accounts, transactions, transfers, bill payments, recipients, loans, savings — and Bank2AI codifies that language as a [Model Context Protocol](https://modelcontextprotocol.io) tool surface. Once a bank speaks Bank2AI, any compliant AI client can read accounts, look up recipients, run spending summaries, and prepare/execute transfers — using the same vocabulary across every bank.

## What Bank2AI gives you

- **A specification.** Eight named MCP tools with fixed input/output JSON Schemas, plus a small set of shared data models — see [Specification](/docs/specification/overview).
- **A Python library.** [`bank2ai`](/docs/library/overview) ships the shared models and a `register_tools` helper on top of [FastMCP](https://github.com/jlowin/fastmcp). Plug in async handlers for the tools you implement — every handler is optional, so you can grow into the full surface incrementally.
- **Reference implementations.** A demo server backed by hardcoded data and example servers backed by real bank APIs — see [Guides](/docs/guides/run-the-demo).
- **A marketplace.** Compliant servers and the agent skills built on top are distributed as a [Claude Code plugin marketplace](/docs/marketplace/overview), installable in one command.

## Who Bank2AI is for

| If you're… | Start here |
| --- | --- |
| A bank or fintech wiring up an MCP server | [Quickstart](/docs/getting-started/quickstart) → [Wrap a real bank](/docs/guides/wrap-a-real-bank) |
| An AI builder integrating bank data | [Specification](/docs/specification/overview) → [Connect from Claude](/docs/guides/connect-claude) |
| Evaluating Bank2AI for your product | [Core concepts](/docs/getting-started/concepts) → [Marketplace](/docs/marketplace/overview) |
| Looking for enterprise support | [Enterprise (Bancony)](/docs/enterprise/overview) |

## Stewarded by Bancony

Bank2AI is freely usable by any bank or fintech. Its development is stewarded by [Bancony](https://bancony.com), which builds enterprise-ready MCP servers, an SDK, an in-channel chat agent (with Generative UI and RAG), and advisory agents on top of the standard. See the [Enterprise](/docs/enterprise/overview) section for details.
