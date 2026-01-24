"""
MCP Server module for Asymmetric.

Provides Model Context Protocol server with dual-mode transport (STDIO/HTTP)
for integration with Claude Code and other MCP clients.
"""

from asymmetric.mcp.server import (
    AsymmetricMCPServer,
    create_server,
    run_server,
)

__all__ = [
    "AsymmetricMCPServer",
    "create_server",
    "run_server",
]
