# Stdio MCP server entry point for Frontier knowledge tools.
from __future__ import annotations

import anyio
from mcp.server.stdio import stdio_server

from frontier_agent.tools import create_knowledge_server


async def main() -> None:
    """Run the knowledge MCP server over stdio."""
    server = create_knowledge_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    anyio.run(main)
