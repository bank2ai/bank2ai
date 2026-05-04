---
title: Changelog
sidebar_position: 2
description: Notable changes to the Bank2AI specification and library.
---

# Changelog

The spec and the Python library version independently. This page tracks notable changes for each.

For the authoritative version field, see [`specs/bank2ai.json`](https://github.com/bank2ai/bank2ai/blob/main/specs/bank2ai.json).

## Specification

### 0.1.0 — Draft

- Initial draft, derived from the Python reference implementation.
- Eight tools: `get-accounts`, `transactions`, `get-categories`, `spending-summary`, `recipients-by-name`, `create-recipient`, `transfer-money-icelandic`, `execute-transfer`.
- Four shared models: `Account`, `Transaction`, `Category`, `Recipient`.
- Authentication declared out of scope.
- A previously specified Bank2AI-defined `authenticate` tool was removed.

## Python library (`bank2ai`)

### 0.1.0

- Initial release.
- Pydantic models for every Bank2AI shape.
- `register_tools(app, ...)` wiring all eight tools onto a FastMCP app.

## Versioning policy

`bank2ai.json` follows [SemVer](https://semver.org/):

- **Major** — breaking changes (removing tools, renaming inputs/outputs, tightening required fields, changing semantic meaning).
- **Minor** — additive changes (new tools, new optional inputs, new optional output fields).
- **Patch** — description / metadata edits with no behavioural impact.

The Python package version moves independently of the spec version.
