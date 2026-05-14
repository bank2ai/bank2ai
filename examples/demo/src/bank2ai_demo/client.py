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
                print(f"  {tx['date']}: {tx['description'][:30]:30s} {tx['amount']:>10,.2f}")
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
                "get-transactions-summary",
                {"group_by": "category", "direction": "Expenses"},
            )
            data = json.loads(result.content[0].text)
            print(f"Total spending: {data['total']:,.2f}")
            print("\nTop spending categories:")
            for item in data["summary"][:5]:
                print(f"  {item.get('categoryId', '-'):24s}: {item['totalAmount']:>10,.2f} ({item['transactionCount']} txs)")
            print()

            # Test 5: Search recipients
            print("Test 5: Search Recipients")
            print("-" * 50)
            result = await session.call_tool("get-recipients", {"name": "Jón"})
            data = json.loads(result.content[0].text)
            print(f"Found {len(data['items'])} recipients matching 'Jón':")
            for recipient in data["items"]:
                ident = recipient["accountIdentifier"]
                routing = ident.get("iban") or ident.get("bban") or ident.get("accountNumber") or ident.get("alias")
                print(f"  {recipient['name']}: {routing} ({recipient.get('nickname') or ''})")
            print()

            # Test 6: Prepare transfer (not executing!)
            print("Test 6: Prepare Transfer (Validation Only)")
            print("-" * 50)
            result = await session.call_tool("prepare-transfer", {
                "debtor_account_id": "acc_checking_001",
                "creditor": {
                    "name": "Jón Jónsson",
                    "accountIdentifier": {
                        "type": "bban",
                        "bban": "0133-26-007890",
                        "country": "IS",
                    },
                    "nationalId": {
                        "value": "010190-1234",
                        "country": "IS",
                        "type": "kennitala",
                    },
                },
                "amount": 100.00,
                "currency": "ISK",
                "rail": "domestic-IS",
                "description": "Demo payment",
            })
            data = json.loads(result.content[0].text)
            print(data["content"])
            item = data.get("item")
            if item is not None:
                summary = item["summary"]
                debtor = summary["debtorAccount"]
                print("\nTransfer details:")
                print(f"  From: {debtor['name']} ({debtor['accountNumber']})")
                print(f"  To: {summary['creditor']['name']} on rail {summary['rail']}")
                print(f"  Amount: {summary['amount']:,.2f} {summary['currency']}")
                print(f"  Intent: {item['transferIntentId']} (expires {item['expiresAt']})")
                print("  Note: This is demo mode - no actual transfer would be executed")
            print()

            print("=" * 50)
            print("Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
