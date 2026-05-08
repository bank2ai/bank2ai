"""Bank2ai Demo Client

A simple client to test the bank2ai demo server.
This demonstrates how to connect to and use bank2ai MCP tools.
"""

import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    """Run the demo client."""
    print("bank2ai Demo Client")
    print("=" * 50)
    print()

    # Start the server as a subprocess
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "bank2ai_demo"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            print("Connected to bank2ai demo server!")
            print()

            # List available tools
            tools_result = await session.list_tools()
            print(f"Available tools: {len(tools_result.tools)}")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description[:60]}...")
            print()

            # Test 1: Get accounts
            print("Test 1: Get Accounts")
            print("-" * 50)
            result = await session.call_tool("get-accounts", {})
            data = json.loads(result.content[0].text)
            print(f"Found {len(data['items'])} accounts:")
            for account in data["items"]:
                print(f"  {account['name']}: {account['balance']:,.2f} {account['currency']}")
            print()

            # Test 2: Get recent transactions
            print("Test 2: Get Recent Transactions")
            print("-" * 50)
            result = await session.call_tool("get-transactions", {"count": 5})
            data = json.loads(result.content[0].text)
            print(f"Last {len(data['items'])} transactions:")
            for tx in data["items"]:
                print(f"  {tx['transaction_date']}: {tx['description'][:30]:30s} {tx['amount']:>10,.2f}")
            print()

            # Test 3: Get categories
            print("Test 3: Get Categories")
            print("-" * 50)
            result = await session.call_tool("get-categories", {})
            data = json.loads(result.content[0].text)
            print(f"Available categories: {', '.join(c['name'] for c in data['items'])}")
            print()

            # Test 4: Transactions summary (expenses only)
            print("Test 4: Transactions Summary by Category (Expenses)")
            print("-" * 50)
            result = await session.call_tool(
                "transactions-summary",
                {"group_by": "category", "direction": "Expenses"},
            )
            data = json.loads(result.content[0].text)
            print(f"Total spending: {data['total']:,.2f}")
            print("\nTop spending categories:")
            for item in data["summary"][:5]:
                print(f"  {item['category']:20s}: {item['total_amount']:>10,.2f} ({item['transaction_count']} txs)")
            print()

            # Test 5: Search recipients
            print("Test 5: Search Recipients")
            print("-" * 50)
            result = await session.call_tool("recipients-by-name", {"name": "Smith"})
            data = json.loads(result.content[0].text)
            print(f"Found {len(data['items'])} recipients matching 'Smith':")
            for recipient in data["items"]:
                print(f"  {recipient['name']}: {recipient['accountNumber']} ({recipient.get('description') or ''})")
            print()

            # Test 6: Prepare transfer (not executing!)
            print("Test 6: Prepare Transfer (Validation Only)")
            print("-" * 50)
            result = await session.call_tool("transfer-money-icelandic", {
                "amount": 100.00,
                "recipient_ssn": "123-45-6789",
                "recipient_account_number": "5678-90-123456",
                "description": "Demo payment",
            })
            data = json.loads(result.content[0].text)
            print(data["content"])
            if "item" in data:
                item = data["item"]
                print(f"\nTransfer details:")
                print(f"  From: {item['withdrawal_account']['name']} ({item['withdrawal_account']['accountNumber']})")
                print(f"  To: {item['recipient_name']} ({item['recipient_account_number']})")
                print(f"  Amount: {item['amount']:,.2f} {item['currency']}")
                print(f"  Note: This is demo mode - no actual transfer would be executed")
            print()

            print("=" * 50)
            print("Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
