---
title: Advisory Agents
sidebar_position: 5
description: A suite of advisory agents that consume the Bank2AI surface to give domain-specific advice.
---

# Advisory Agents

Bancony's Advisory Agents are a suite of domain-specific AI agents that consume the [Bank2AI](/docs/specification/overview) tool surface to give grounded financial advice — with the bank's data and the bank's policies in the loop.

## The current suite

| Agent | What it advises on |
| --- | --- |
| **Budgeting Agent** | Reads spending, compares to user-set targets, flags overruns, suggests adjustments. |
| **Savings Agent** | Spots surplus cash flow, recommends savings vehicles, sets up auto-savings rules. |
| **Mortgage Agent** | Walks customers through mortgage scenarios using their actual income/spending data. |
| **Retirement Agent** | Long-horizon planning grounded in the customer's contribution and balance history. |
| **Cash-flow Agent** | Forecasts upcoming inflows and outflows from transaction patterns. |

Each agent is built as a [skill](/docs/marketplace/overview) in the Bank2AI sense — it depends on tool *names*, not on bank identity. Run any of them against any compliant Bank2AI server.

## Why advisory agents need a standard

Advice is only as good as the data behind it. Without a standard, every advisory product would have to integrate per-bank, with bespoke schemas, bespoke auth, bespoke transfers — and the cost of supporting more banks would scale linearly.

Bank2AI fixes that. An advisory agent against `bank2ai-acme` works the same way against `bank2ai-yourbank` or any other compliant server. The agent stays focused on advice; the standard handles the plumbing.

## Bank-side controls

Banks deploying Advisory Agents stay in control of:

- **Which agents are exposed.** A bank can offer all five, a subset, or whitelist its own.
- **Confirmation policies.** Anything that moves money still goes through the Bank2AI prepare → execute split, gated on the bank's confirmation UI.
- **Compliance posture.** Audit logs and policy checks live in the Bank2AI server, not in the agent.

[Get in touch](./contact) to discuss a deployment.
