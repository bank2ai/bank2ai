---
title: Publishing a skill
sidebar_position: 3
description: How to publish an agent skill that consumes Bank2AI to the marketplace.
---

# Publishing a skill

Skills are the high-leverage layer of Bank2AI: write once, work against every compliant bank server. Here's how to ship one.

## Prerequisites

- A working skill (a `SKILL.md` plus any supporting prompts/resources).
- A clear declaration of which Bank2AI tools the skill needs.
- A demo or test against `bank2ai-demo` showing the skill behaves correctly with the reference server.

## Package as a Claude Code plugin

```
bank2ai-budgeting-helper/
├── plugin.json
└── SKILL.md
```

Example `plugin.json`:

```json
{
  "name": "bank2ai-budgeting-helper",
  "version": "0.1.0",
  "description": "Compare spending against budget targets and flag overruns.",
  "type": "skill",
  "requires": [
    "bank2ai/0.1",
    "bank2ai:transactions",
    "bank2ai:spending-summary",
    "bank2ai:get-categories"
  ],
  "homepage": "https://github.com/your-org/bank2ai-budgeting-helper"
}
```

The `requires` field declares both the spec version and the specific tools your skill needs. Installers can warn users whose currently installed server doesn't register all of them.

## Submit to the registry

Same flow as servers — fork [`bank2ai/bank2ai-marketplace`](https://github.com/bank2ai/bank2ai-marketplace), add an entry, open a PR.

## Skill review checklist

- **Tool-only dependencies.** The skill works against any compliant Bank2AI server, not just one bank.
- **Honest in `requires`.** It declares every tool it actually uses, no more.
- **Confirms before executing.** If the skill triggers transfers, it always goes through `transfer-money-icelandic` first and surfaces the prepared item to the user.
- **Tolerates unknown fields.** Doesn't break when a server returns extras on `Account` / `Transaction` / `Recipient`.
- **Localized prompts.** If the skill assumes a locale, it says so up front (and ideally is structured so other locales can be added).

See [Build an agent skill](/docs/guides/build-a-skill) for the full design guidance.
