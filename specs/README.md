# Bank2AI MCP Specification

This directory holds the language-neutral specification for the **Bank2AI** [Model Context Protocol](https://modelcontextprotocol.io) tool surface — the same set of tools every Bank2AI server is expected to expose, regardless of programming language or backend.

## Files

| File                 | Purpose                                                                                |
| -------------------- | -------------------------------------------------------------------------------------- |
| `bank2ai.spec.md`    | Narrative spec — overview, lifecycle, per-tool semantics, auth protocol, error model.  |
| `bank2ai.json`       | Machine-readable: `version`, full `tools[]` (with `inputSchema` and `outputSchema` as JSON Schema), reusable `models{}`, and the `auth` protocol descriptor. |

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
* **Auto-generating bindings:** the `models{}` block contains standalone schemas for shared types (`Account`, `Transaction`, `Category`, `Recipient`, `AuthParam`, `AuthResponse`) suitable for JSON-Schema-based code generators.

## Reference implementations

* [`examples/demo`](../examples/demo) — full surface backed by hardcoded data; useful for client-side conformance testing.
* [`examples/meniga`](../examples/meniga) — full surface backed by the [Meniga](https://meniga.com) API; demonstrates the credential-based auth flow.
