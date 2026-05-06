---
title: Build an agent skill
sidebar_position: 5
description: How to build agent skills on top of the bank2ai tool surface.
---

# Build an agent skill on top of bank2ai

A *skill* is a small package of prompts, tool conventions, and orchestration logic that an AI agent can use to do something useful with a bank2ai server. Skills are the high-leverage layer, once a bank speaks bank2ai, every skill works against it for free.

## What a skill is

In the Claude Code plugin format, a skill is a directory of:

- a `SKILL.md` file describing what the skill does and when to invoke it,
- optional resources (templates, examples),
- a manifest declaring required bank2ai capabilities (e.g. *"requires `get-transactions` and `spending-summary`"*).

See the [Claude Code plugin marketplace docs](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces) for the full format.

## Examples of useful skills

| Skill | What it does | Tools it uses |
| --- | --- | --- |
| **Budgeting helper** | Compares spending vs. budget targets and flags overruns | `get-transactions`, `spending-summary`, `get-categories` |
| **Statement explainer** | Walks the user through a recent statement, summarising and answering questions | `get-transactions` |
| **Transfer assistant** | Helps users prepare and confirm transfers, including recipient lookup and validation | `recipients-by-name`, `create-recipient`, `transfer-money-icelandic`, `execute-transfer` |
| **Subscription auditor** | Detects recurring charges and surfaces them | `get-transactions` |
| **Cash-flow forecaster** | Projects forward from past patterns | `get-transactions`, `get-accounts` |

## Design guidelines

- **Depend on tool names, not server identity.** A skill that works for one bank2ai server should work for any of them. Don't hardcode bank-specific behaviour.
- **Honour the prepare → execute split.** Never call `execute-transfer` without first calling `transfer-money-icelandic` and surfacing the prepared item to the user for confirmation.
- **Tolerate unknown fields.** Servers MAY return extras on `Account`, `Transaction`, etc. Don't break when you see them.
- **Be explicit about required tools.** Declare which bank2ai tools your skill depends on, so installers can warn the user if their server doesn't register them.

## Publishing

When ready, publish your skill to the [marketplace](/docs/marketplace/publishing-a-skill). Once listed, any Claude Code user can install it with `/plugin install bank2ai/<skill-name>`.
