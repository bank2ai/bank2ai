"""Run the Bank2AI demo MCP server: ``python -m bank2ai_demo``."""

import asyncio

from .server import main


if __name__ == "__main__":
    asyncio.run(main())
