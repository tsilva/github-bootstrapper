"""MCP (Model Context Protocol) server for gitfleet.

This module provides an MCP server that exposes gitfleet's multi-repo
operations as tools that can be orchestrated by Claude.
"""

from .server import main
from .logging_utils import setup_mcp_logging, get_mcp_logger
from .tools import (
    exec_command_parallel,
    exec_claude_single,
    list_repos,
    sync_repos,
    get_status,
)

__all__ = [
    "main",
    "setup_mcp_logging",
    "get_mcp_logger",
    "exec_command_parallel",
    "exec_claude_single",
    "list_repos",
    "sync_repos",
    "get_status",
]
