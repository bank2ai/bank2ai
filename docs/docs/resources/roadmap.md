---
title: Roadmap
sidebar_position: 1
description: What's next for the bank2ai specification, library, and marketplace.
---

# Roadmap

The bank2ai roadmap is intentionally narrow: keep the spec small, deepen the conformance story, and grow the marketplace.

## Specification

- **Flip the source-of-truth relationship.** Today the spec is *derived from* the Python reference implementation; a drift test prevents desync. Long-term, the spec should be hand-authored and implementations validated against it. Tracked in the repo under [`specs/README.md`](https://github.com/bank2ai/bank2ai/blob/main/specs/README.md#status).
- **International transfers.** `prepare-transfer-icelandic` is the current domestic-transfer tool. We expect to add SEPA / SWIFT / domestic equivalents in other markets as additive minor versions.
- **Loans, savings products, cards-as-objects.** bank2ai today covers accounts, transactions, and transfers. Loans and dedicated savings products are the most-requested next domains.

## Library

- **Conformance test suite.** A standalone package (`bank2ai-conformance`) that any server can run against itself.
- **Async streaming for `get-transactions`.** For banks with large transaction histories, streaming results would beat collecting them all in memory.

## Marketplace

- **Public registry online.** [`github.com/bank2ai/marketplace`](https://github.com/bank2ai/marketplace) bootstrapped with the demo and reference bank servers.
- **Compatibility matrix.** A page listing every published server with the spec versions and tools it supports.

## Out of scope

- **Authentication standardization.** Banks differ; bank2ai deliberately stays out of authentication. See [Authentication](/docs/specification/overview#4-authentication).
- **A bespoke transport.** MCP is the transport; we're not inventing another one.

## Suggesting changes

Open an issue at [github.com/bank2ai/bank2ai/issues](https://github.com/bank2ai/bank2ai/issues) describing the use case. Concrete bank or skill examples beat abstract requests.
