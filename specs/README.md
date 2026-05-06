# Bank2ai MCP Specification

Bank2ai connects digital banking data and operations with AI agents. The language of banking — accounts, transactions, transfers, bill payments, recipients, loans, savings — is universal, and bank2ai codifies that language as an open standard so banks and fintechs can collaborate on AI tools and skills instead of each rebuilding the same surface.

This directory holds the language-neutral specification for the bank2ai [Model Context Protocol](https://modelcontextprotocol.io) tool surface — the same set of tools every bank2ai server is expected to expose, regardless of programming language or backend.

> **Where the marketplace fits in.** The spec defines the *contract*; the [bank2ai marketplace](../README.md#marketplace) is where compliant servers and skills are distributed. The marketplace is packaged as a [Claude Code plugin marketplace](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces), so any Claude Code user can install a bank2ai server or skill with a single command — and any other client that speaks that plugin format can consume the same registry.

## Files

| File                 | Purpose                                                                                |
| -------------------- | -------------------------------------------------------------------------------------- |
| `bank2ai.spec.md`    | Narrative spec — overview, lifecycle, per-tool semantics, error model.                 |
| `bank2ai.json`       | Machine-readable: `version`, full `tools[]` (with `inputSchema` and `outputSchema` as JSON Schema), and reusable `models{}`. |

## Status

**Draft.** The spec is currently *derived from* the [Python reference implementation](../src/bank2ai) under [`src/bank2ai/`](../src/bank2ai). When the Python package's tool registrations or models change, run:

```bash
uv run python scripts/generate_spec.py
```

…to regenerate `bank2ai.json`. A drift test in `examples/demo/tests/test_schema_sync.py` fails CI if the committed file is out of date.

Long-term we'd like to flip the relationship: hand-author this spec as the contract, and have implementations validate against it. That's not yet in place.

## Versioning

`bank2ai.json` exposes a top-level `version` (currently `0.1.0`) that follows [SemVer](https://semver.org/):

* **Major** bumps for breaking changes — removing tools, renaming inputs/outputs, tightening required fields, changing semantic meaning.
* **Minor** bumps for additive changes — new tools, new optional inputs, new optional output fields.
* **Patch** bumps for description / metadata edits with no behavioural impact.

The Python package (`bank2ai`) versions independently of the spec.

## Consuming the spec

* **Building a new server (any language):** read `bank2ai.spec.md` for semantics, then validate request/response payloads against the JSON Schemas in `bank2ai.json`.
* **Building a client / agent:** rely on each server's MCP `tools/list` response — but the schemas in `bank2ai.json` are authoritative and clients can use them to render forms, validate parameters, or generate typed bindings.
* **Auto-generating bindings:** the `models{}` block contains standalone schemas for shared types (`Account`, `Transaction`, `Category`, `Recipient`) suitable for JSON-Schema-based code generators.

## Reference implementations

* [`examples/demo`](../examples/demo) — full surface backed by hardcoded data; useful for client-side conformance testing.

