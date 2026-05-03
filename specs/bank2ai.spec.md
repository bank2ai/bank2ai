# Bank2AI MCP Specification

> **Version:** 0.1.0 — draft, derived from the Python reference implementation.
> **Companion artifact:** [`bank2ai.json`](./bank2ai.json) — canonical input/output JSON Schemas.

Bank2AI defines a single [Model Context Protocol](https://modelcontextprotocol.io) tool surface that any bank can expose so AI agents (and through them, end customers) can read accounts and transactions, look up recipients, run spending summaries, and prepare/execute transfers — using the same tool surface across every bank.

The contract has three parts:

1. The **tool surface** — eight named MCP tools whose input and output JSON Schemas are fixed by the spec.
2. The **shared data models** — `Account`, `Transaction`, `Category`, `Recipient`, plus the auth types — used inside tool inputs and outputs.
3. The **authentication protocol** — a small contract servers follow if they need credentials before serving the surface.

> **About RFC 2119 keywords.** *MUST*, *SHOULD*, *MAY* are used per [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).

## 1. Tool surface

Every Bank2AI server MUST register the following tools, with the names below. Input and output shapes are defined by the JSON Schemas in [`bank2ai.json`](./bank2ai.json) under `tools[].inputSchema` and `tools[].outputSchema`.

| Name                       | Purpose                                                            |
| -------------------------- | ------------------------------------------------------------------ |
| `get-accounts`             | List bank accounts and cards, optionally filtered by type or by withdrawal-eligibility. |
| `transactions`             | List transactions, with filters for date range, direction, categories, free-text search, and result count. |
| `get-categories`           | List the bank's transaction categories.                            |
| `spending-summary`         | Aggregated spending grouped by category, group, month, or merchant. |
| `recipients-by-name`       | Lookup saved payment recipients by partial name match.             |
| `create-recipient`         | Save a new recipient for future transfers.                         |
| `transfer-money-icelandic` | **Prepare** a domestic transfer; validates inputs and returns details for confirmation. Does **not** execute. |
| `execute-transfer`         | Execute a transfer that the user has already confirmed.            |

Servers MAY register additional, vendor-specific tools, but they MUST NOT alter the names, inputs, or outputs of the above eight.

> **Why "prepare → execute"?** Splitting transfers into two tools keeps the AI agent on a safe rail: the agent gathers details, the user confirms in their UI, and only then is `execute-transfer` called. Servers SHOULD reject `execute-transfer` calls that don't correspond to a recently prepared transfer.

## 2. Lifecycle

A typical Bank2AI session looks like this:

1. The MCP client connects and calls `tools/list`. The server returns the eight Bank2AI tools (plus, if applicable, an `authenticate` tool — see §4).
2. If the server requires authentication, the client either invokes `authenticate` directly (LLM-driven) or has its `elicitation` capability used by the server to collect credentials interactively (§4).
3. The client calls Bank2AI tools as the user requests them. The server applies the auth gate to every non-`authenticate` call.
4. On a transfer, the client calls `transfer-money-icelandic` first to validate, surfaces the prepared details to the user, and only invokes `execute-transfer` after explicit confirmation.

## 3. Shared data models

The schemas in `bank2ai.json` under `models{}` define the canonical shapes for:

* **`Account`** — id, accountNumber, currency, balance, optional availableBalance, overdraftLimit, isWithdrawalAccount, isDefaultAccount, accountType (`Current` | `Savings` | `Credit`).
* **`Transaction`** — id, description, amount (negative = expense), transaction_date (ISO 8601), category.
* **`Category`** — id, name (localized).
* **`Recipient`** — id, name, accountNumber, accountNumberType (`Domestic` | `IBAN` | `SWIFT`), socialSecurityNumber, optional bankInfo, paymentType, address, isFavorite, description.
* **`AuthParam`** — id, title, type (`text` | `password`).
* **`AuthResponse`** — authenticated, message, required_parameters, session_parameters, token, culture.

Servers MAY return additional fields on these objects; clients MUST tolerate unknown fields. Servers MUST NOT omit fields marked `required` in the schemas.

## 4. Authentication protocol

A server that requires credentials MUST follow this flow:

1. **Initial unauthenticated state.** Before any non-`authenticate` tool call, the server attempts an internal `authenticate(parameters=[])` call. If it returns `authenticated=false` with a non-empty `required_parameters[]`, the server enters the *credentials-required* state.

2. **Exposing the dynamic `authenticate` tool.** The server MUST expose an `authenticate` tool whose input schema matches the `required_parameters` returned in step 1 (one string property per `AuthParam.id`, with `password`-typed params marked using `x-password: true` or equivalent). The tool's role is to receive the credentials and complete authentication.

3. **Inline collection via elicitation (optional).** If the MCP client advertises the `elicitation` capability, the server MAY call `elicit_form` with the same schema before each non-`authenticate` tool call, instead of (or in addition to) returning an "auth required" error. The server MUST honour user cancellation.

4. **Per-call enforcement.** The server MUST gate every non-`authenticate` tool call on a successful auth state. On a tool error after a successful call, the server SHOULD invalidate the session and retry once after re-authenticating.

5. **No-auth servers.** Servers backed by demo data or system credentials (no end-user authentication) MUST NOT register an `authenticate` tool. The `authenticate` tool's presence is the signal to clients that credentials are required.

The reference implementations of this protocol are in [`src/bank2ai/mcp.py`](../src/bank2ai/mcp.py) — `make_auth_middleware` and `register_authenticate_tool`.

## 5. Error model

* Servers SHOULD return MCP `ToolError` (or equivalent protocol-level error) for unrecoverable failures.
* For recoverable user-facing conditions (e.g. "Insufficient funds", "Invalid recipient"), servers SHOULD return a successful tool call whose response model includes a human-readable `content` field describing the problem. `transfer-money-icelandic` and `create-recipient` model this explicitly.
* Authentication failures MUST surface a non-empty `AuthResponse.message` that the client can display to the end user.

## 6. Localization

* All money amounts are numeric in their account's currency; currencies are ISO 4217 (`USD`, `ISK`, `EUR`, …).
* Dates are ISO 8601 (`YYYY-MM-DD`).
* Category names are localized server-side. Clients MUST treat category names as opaque user-facing strings; programmatic filtering MUST go through the `categories` parameter on `transactions` / `spending-summary` (which references category names returned by `get-categories`).

## 7. Backwards compatibility

The spec versioning policy lives in [`README.md`](./README.md). Notable additive-change rules:

* Adding a new optional tool input is a **minor** bump.
* Adding a new optional output field is a **minor** bump; clients MUST tolerate unknown fields.
* Adding a new tool is a **minor** bump.
* Removing or renaming anything, or making a previously optional field required, is a **major** bump.

## 8. Reference implementations

* [`examples/demo`](../examples/demo) — full surface backed by hardcoded data; useful for client conformance testing without a real bank.
* [`examples/meniga`](../examples/meniga) — full surface backed by the [Meniga](https://meniga.com) API; demonstrates the auth protocol with `email` + `password`.
