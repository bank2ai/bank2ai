# Bank2AI Demo Server

A reference implementation of the Bank2AI specification using hardcoded test data.

## Purpose

This demo server demonstrates how to implement a Bank2AI-compliant MCP server. It uses realistic hardcoded test data instead of connecting to real banking systems, making it perfect for:

- Testing AI agents during development
- Learning how to implement the Bank2AI specification
- Demonstrating Bank2AI tools to stakeholders
- Integration testing without needing real bank accounts

## Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the Demo Server

The server uses stdio transport for MCP communication:

```bash
python server.py
```

### 3. Test with the Demo Client

In another terminal:

```bash
source venv/bin/activate  # Activate the same venv
python client.py
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
      "command": "python",
      "args": ["/path/to/bank2ai/demo/server.py"],
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
    command="python",
    args=["/path/to/bank2ai/demo/server.py"],
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

Edit `data.py` to customize:

- Account balances and types
- Transaction history
- Categories
- Recipients

The `generate_transactions()` function creates realistic transaction patterns - modify it to test different scenarios.

## Architecture

```
demo/
├── server.py          # MCP server implementation
├── data.py            # Hardcoded test data
├── client.py          # Test client
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

### server.py

- Implements all 8 Bank2AI tools
- Uses MCP SDK for protocol handling
- Stdio transport for maximum compatibility
- Filters and transforms test data based on tool parameters

### data.py

- Defines ACCOUNTS, TRANSACTIONS, CATEGORIES, RECIPIENTS
- Generates realistic transaction history
- Easy to modify for testing different scenarios

### client.py

- Demonstrates connecting to the MCP server
- Shows example usage of each tool
- Good starting point for integration testing

## Extending the Demo

### Adding New Tools

1. Add the tool definition to `server.py`:
```python
TOOL_MY_TOOL = Tool(
    name="my-tool",
    description="...",
    inputSchema={...}
)
```

2. Add the tool to `list_tools()`:
```python
return [
    ...,
    TOOL_MY_TOOL,
]
```

3. Add handler logic to `call_tool()`:
```python
elif name == "my-tool":
    # Implementation here
    return [TextContent(type="text", text=json.dumps(result))]
```

### Adding More Test Data

Edit `data.py` and add to the appropriate list:

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
python client.py
```

Expected output:
- ✅ All 8 tools should be listed
- ✅ All test cases should pass
- ✅ No errors or exceptions

## Troubleshooting

### "Module not found: mcp"

Install dependencies:
```bash
pip install -r requirements.txt
```

### "Permission denied" errors

Make sure you've activated the virtual environment:
```bash
source venv/bin/activate
```

### Server doesn't respond

The server uses stdio - it should be run as a subprocess by an MCP client, not standalone. Use `client.py` to test.

## Next Steps

1. **For Banks**: Use this as a template to build your production implementation
2. **For AI Developers**: Use this for development and testing before connecting to real banks
3. **For Contributors**: Extend the demo to test new tool proposals

## License

MIT License - see [../LICENSE](../LICENSE) for details.
