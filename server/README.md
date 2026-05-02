# Bank2AI Reference Server

A reference MCP server implementation of the [Bank2AI specification](https://github.com/bank2ai/spec). The Bank2AI tool surface (names, input/output schemas, descriptions) lives in a single shared module — `bank2ai_mcp.py` — and each backend ships as its own MCP server that imports the shared spec and provides handler callables.

Two servers are included out of the box:

- **`demo_server.py`** — backed by hardcoded data in `demo_data.py`. Great for testing AI agents, demonstrations, and integration testing without a real bank.
- **`meniga_server.py`** — backed by Meniga APIs (`api.meniga.cloud` / `api.meniga.is`) as an example of wiring a real bank behind the same Bank2AI surface.

To add another bank, write a `<bank>_server.py` that imports `register_tools` from `bank2ai_mcp` and supplies handler callables — no need to redefine schemas.

## Quick Start

This project uses [uv](https://docs.astral.sh/uv/) for environment and dependency management.

### 1. Install Dependencies

```bash
uv sync
```

To include test extras as well:

```bash
uv sync --group test
```

### 2. Run the Demo Server

The server uses stdio transport for MCP communication:

```bash
uv run python demo_server.py
```

To run the Meniga-backed server instead (requires `BANK2AI_MENIGA_BASE_URL` and credentials — see `meniga_server.py` for the full env var list):

```bash
uv run python meniga_server.py
```

### 3. Test with the Demo Client

In another terminal:

```bash
uv run python client.py
```

This will run through a series of test cases demonstrating all the Bank2AI tools.

## Test Data

The demo server includes:

### Accounts (3)
- **Main Checking** - $5,420.50 balance
- **Emergency Fund** - $15,000.00 balance
- **Visa Credit Card** - -$850.25 balance (credit available: $4,149.75)

### Transactions (~30)
- 90 days of realistic transaction history
- Categories: Income, Housing, Groceries, Transportation, Entertainment, Utilities, Dining, Healthcare, Shopping
- Mix of recurring and one-time transactions

### Categories (9)
Income, Housing, Groceries, Transportation, Entertainment, Utilities, Dining, Healthcare, Shopping

### Recipients (4)
- Jane Smith (Friend)
- John Doe (Contractor)
- Alice Johnson (Family)
- Bob Williams (Landlord)

## Implemented Tools

All 8 Bank2AI tools are fully implemented:

| Tool | Status |
|------|--------|
| `get-accounts` | ✅ Implemented |
| `transactions` | ✅ Implemented |
| `get-categories` | ✅ Implemented |
| `spending-summary` | ✅ Implemented |
| `recipients-by-name` | ✅ Implemented |
| `create-recipient` | ✅ Implemented (simulated) |
| `transfer-money-icelandic` | ✅ Implemented (validation only) |
| `execute-transfer` | ✅ Implemented (simulated) |

**Note**: Transfer tools (`create-recipient`, `transfer-money-icelandic`, `execute-transfer`) simulate operations but don't modify data. In a real implementation, these would interact with banking APIs.

## Using with AI Agents

### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "bank2ai-demo": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/bank2ai-server",
        "run", "python", "demo_server.py"
      ],
      "env": {}
    }
  }
}
```

### LangGraph / LangChain

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="uv",
    args=[
        "--directory", "/path/to/bank2ai-server",
        "run", "python", "demo_server.py",
    ],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # List tools
        tools = await session.list_tools()
        
        # Call a tool
        result = await session.call_tool("get-accounts", {})
```

### Custom MCP Client

Any MCP-compatible client can connect to this server using stdio transport.

## Customizing Test Data

Edit `demo_data.py` to customize:

- Account balances and types
- Transaction history
- Categories
- Recipients

The `generate_transactions()` function creates realistic transaction patterns - modify it to test different scenarios.

## Architecture

```
server/
├── bank2ai_mcp.py               # Shared Bank2AI tool spec: names,
│                                # input/output schemas, Pydantic response
│                                # models, register_tools() helper, and
│                                # optional auth middleware/tool
├── demo_server.py               # Demo MCP server (uses bank2ai_mcp + demo_data)
├── demo_data.py                 # Hardcoded demo accounts/txns/categories/recipients
├── meniga_server.py             # Meniga-backed MCP server
├── client.py                    # Test client (talks to demo_server)
├── test_schema_sync.py          # Verifies tool registration matches the spec
├── pyproject.toml               # Python project & dependencies (uv)
├── uv.lock                      # Locked dependency versions
└── README.md                    # This file
```

### bank2ai_mcp.py

- Single source of truth for the Bank2AI MCP surface: tool names,
  descriptions, input parameters (with `Field` annotations), and the
  Pydantic response models that FastMCP turns into tool output schemas.
- `register_tools(app, *, get_accounts=, get_transactions=, ...)` wires
  the entire surface onto a `FastMCP` app, dispatching to caller-supplied
  async handler callables.
- Optional `make_auth_middleware()` and `register_authenticate_tool()`
  helpers for servers that need credential-based authentication.

### demo_server.py / demo_data.py

- `demo_server.py` provides handler callables that read from `demo_data.py`.
- `demo_data.py` defines `ACCOUNTS`, `TRANSACTIONS`, `CATEGORIES`,
  `RECIPIENTS` with `generate_transactions()` for realistic history.
- No authentication; this server is for offline/local use.

### meniga_server.py

- Same shape as `demo_server.py`, but its handlers call into Meniga APIs.
- Registers the auth middleware and a dynamic `authenticate` tool that
  collects `email` / `password` (via MCP elicitation when supported).

### client.py

- Demonstrates connecting to a Bank2AI MCP server (defaults to
  `demo_server.py`).
- Shows example usage of each tool.
- Good starting point for integration testing.

## Extending the Demo

### Adding New Tools

Add a new tool to the shared spec by editing `bank2ai_mcp.py`:

1. Define the input parameters and `output_schema` inside `register_tools()`,
   following the existing tools as a template, and dispatch to a new handler
   keyword arg.
2. Add the matching keyword argument to the `register_tools` signature.
3. Implement the handler in each server (`demo_server.py`, `meniga_server.py`).
4. Pass it in the corresponding `register_tools(...)` call.

This way the input schema, output schema, name, and description are defined
exactly once for all backends.

### Adding More Test Data

Edit `demo_data.py` and add to the appropriate list:

```python
ACCOUNTS.append({
    "id": "acc_new_001",
    "name": "Investment Account",
    ...
})
```

## Testing

Run the test client to verify all tools work:

```bash
uv run python client.py
```

Expected output:
- ✅ All 8 tools should be listed
- ✅ All test cases should pass
- ✅ No errors or exceptions

## Troubleshooting

### "Module not found: mcp"

Install dependencies:
```bash
uv sync
```

### "Permission denied" errors

Run commands through `uv run` so the managed virtual environment is used:
```bash
uv run python server.py
```

### Server doesn't respond

The server uses stdio - it should be run as a subprocess by an MCP client, not standalone. Use `client.py` to test.

## Next Steps

1. **For Banks**: Use this as a template to build your production implementation
2. **For AI Developers**: Use this for development and testing before connecting to real banks
3. **For Contributors**: Extend the demo to test new tool proposals

## License

MIT License - see [LICENSE](./LICENSE) for details.
