---
title: Bancony SDK
sidebar_position: 3
description: A higher-level SDK that simplifies implementing bank2ai MCP servers.
---

# Bancony SDK

The Bancony SDK is a higher-level toolkit for teams building bank2ai MCP servers. It sits *on top of* the open `bank2ai` library and adds the bits every bank ends up writing themselves.

## What's in the SDK

- **Handler scaffolding.** Opinionated patterns for credential exchange, rate-limiting, idempotency, and retries, pre-wired so you fill in the bank-specific bits.
- **Mapper helpers.** Type-safe utilities for translating between common bank API shapes and the bank2ai shape, with property-based tests included.
- **Two-step transfer state.** A pluggable backing store (in-memory, Redis, your DB) for the prepare → execute flow, with sensible defaults for token expiry and replay protection.
- **Auth adapters.** Pre-built integrations for common identity providers (OAuth2, SAML, customer auth APIs) surfaced as drop-in middleware.
- **Test fixtures.** Conformance fixtures that exercise every tool against your server with realistic edge cases.

## Spec compliance

The SDK does not change the bank2ai surface, it accelerates implementing it. Servers built with the SDK pass the same [drift test](/docs/library/testing#1-spec-drift-test) as servers built directly on `bank2ai`.

## Open standard, supported toolkit

You can implement bank2ai without the SDK using only the open library, that path is documented under [Python library](/docs/library/overview) and [Guides](/docs/guides/wrap-a-real-bank). The SDK is for teams that want a faster, supported path with the production patterns already baked in.

[Get in touch](./contact) for access and pricing.
