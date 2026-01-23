"""MCP server for gitfleet.

This module implements the MCP server that exposes gitfleet's multi-repo
operations as tools that can be orchestrated by Claude.
"""

import asyncio
import json
import time
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import (
    list_repos,
    exec_command,
    sync_repos,
    get_status,
    RepoInfo,
    ExecutionResult,
    SyncResult,
    StatusSummary,
)
from .logging_utils import (
    setup_mcp_logging,
    get_mcp_logger,
    log_tool_invocation,
    log_summary,
)

# Logger will be configured in main()
logger = get_mcp_logger()

# Create MCP server
server = Server("gitfleet")


# ============================================================================
# Tool definitions
# ============================================================================

TOOLS = [
    Tool(
        name="gitfleet_list_repos",
        description="""List and filter GitHub repositories using gh CLI (no token needed).

Use this tool to discover repositories before running operations.

Examples:
- List authenticated user's repos: source="github"
- List specific user's repos: source="github:username"
- List local repos only: source="local"
- List specific repos: source="repo1,repo2,repo3"
- Filter by language: filters=["language:python", "!archived"]
- Filter by owner: filters=["owner:mycompany", "!fork"]

Supported filters:
- "!archived" - exclude archived repos (default)
- "!fork" - exclude forked repos (default)
- "archived" - include archived repos
- "fork" - include forked repos
- "language:X" - filter by language
- "owner:X" - filter by owner/org
- "pattern:X" - filter by glob pattern (e.g., "pattern:my-*")
- "private" - only private repos
- "public" - only public repos""",
        inputSchema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Repository source: 'github:username', 'local', or comma-separated repo names"
                },
                "filters": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter strings. Archived and forked repos are excluded by default. Use 'archived' or 'fork' to include them.",
                    "default": []
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to return (default: ['name']). Use ['all'] for all fields. Available: name, full_name, description, language, private, fork, archived, default_branch, html_url, local_path, exists_locally",
                    "default": ["name"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Max repos to return (default: 100, max: 1000)",
                    "default": 100
                }
            },
            "required": ["source"]
        }
    ),
    Tool(
        name="gitfleet_exec",
        description="""Execute commands across multiple repositories.

This is the main workhorse tool for running operations across repos.

Command prefixes:
- "claude:" - Run Claude CLI with a prompt (e.g., "claude:Add a LICENSE file")
- "claude:/" - Run a Claude skill (e.g., "claude:/readme-generator")
- "gh:" - Run GitHub CLI command (e.g., "gh:pr list")
- "git:" - Run git command (e.g., "git:status")
- No prefix - Run shell command (e.g., "npm install")

Examples:
- Run Claude skill: repos=["repo-a", "repo-b"], command="claude:/readme-generator"
- Run Claude prompt: repos=["repo-a"], command="claude:Add comprehensive docstrings"
- Run git command: repos=["repo-a", "repo-b"], command="git:status"
- Run shell command: repos=["repo-a"], command="npm install"

The tool returns structured results showing which repos succeeded, failed, or were skipped.""",
        inputSchema={
            "type": "object",
            "properties": {
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of repository names to execute on"
                },
                "command": {
                    "type": "string",
                    "description": "Command to execute (with optional prefix: claude:, gh:, git:)"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview without executing (default: false)",
                    "default": False
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds per repo (default: 300)",
                    "default": 300
                }
            },
            "required": ["repos", "command"]
        }
    ),
    Tool(
        name="gitfleet_sync",
        description="""Sync repositories by cloning new repos and/or pulling updates.

Operations:
- "sync" (default): Clone missing repos AND pull updates for existing ones
- "clone": Only clone repos that don't exist locally
- "pull": Only pull updates for repos that exist locally

Repos with uncommitted changes are skipped during pull to prevent data loss.

Example: repos=["repo-a", "repo-b"], operation="sync" """,
        inputSchema={
            "type": "object",
            "properties": {
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of repository names to sync"
                },
                "operation": {
                    "type": "string",
                    "enum": ["sync", "clone", "pull"],
                    "description": "Sync operation type (default: sync)",
                    "default": "sync"
                }
            },
            "required": ["repos"]
        }
    ),
    Tool(
        name="gitfleet_status",
        description="""Get synchronization status of repositories.

Returns repos categorized by their status:
- in_sync: Up to date with remote
- unpushed: Local commits not pushed
- unpulled: Remote commits not pulled
- diverged: Both local and remote have new commits
- uncommitted: Has uncommitted changes
- detached: HEAD is detached
- no_remote: No remote tracking branch
- not_cloned: Repository not cloned locally

Use this to understand the state of repos before running operations.""",
        inputSchema={
            "type": "object",
            "properties": {
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of repository names to check"
                }
            },
            "required": ["repos"]
        }
    )
]


# ============================================================================
# MCP server handlers
# ============================================================================

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Return list of available tools."""
    return TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool invocation."""
    log_tool_invocation(name, arguments, logger)
    start_time = time.time()

    try:
        if name == "gitfleet_list_repos":
            fields = arguments.get("fields", ["name"])
            limit = arguments.get("limit", 100)
            result = list_repos(
                source=arguments["source"],
                filters=arguments.get("filters", []),
                fields=fields,
                limit=limit
            )
            # Convert to serializable format with field selection
            output = {
                "count": len(result),
                "repos": [r.to_dict(fields) for r in result]
            }
            duration_ms = int((time.time() - start_time) * 1000)
            log_summary(
                name, total=len(result), success=len(result),
                failed=0, skipped=0, duration_ms=duration_ms, logger=logger
            )

        elif name == "gitfleet_exec":
            result = exec_command(
                repos=arguments["repos"],
                command=arguments["command"],
                dry_run=arguments.get("dry_run", False),
                timeout=arguments.get("timeout", 300)
            )
            output = result.to_dict()
            duration_ms = int((time.time() - start_time) * 1000)
            log_summary(
                name, total=result.total, success=len(result.success),
                failed=len(result.failed), skipped=len(result.skipped),
                duration_ms=duration_ms, logger=logger
            )

        elif name == "gitfleet_sync":
            result = sync_repos(
                repos=arguments["repos"],
                operation=arguments.get("operation", "sync")
            )
            output = result.to_dict()
            duration_ms = int((time.time() - start_time) * 1000)
            total = len(result.cloned) + len(result.pulled) + len(result.skipped) + len(result.failed)
            log_summary(
                name, total=total, success=len(result.cloned) + len(result.pulled),
                failed=len(result.failed), skipped=len(result.skipped),
                duration_ms=duration_ms, logger=logger
            )

        elif name == "gitfleet_status":
            result = get_status(repos=arguments["repos"])
            output = result.to_dict()
            duration_ms = int((time.time() - start_time) * 1000)
            log_summary(
                name, total=result.total, success=result.total,
                failed=0, skipped=0, duration_ms=duration_ms, logger=logger
            )

        else:
            logger.warning(f"Unknown tool requested: {name}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]

        return [TextContent(
            type="text",
            text=json.dumps(output, indent=2)
        )]

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.exception(f"Error executing tool {name} after {duration_ms}ms")
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)})
        )]


# ============================================================================
# Entry point
# ============================================================================

def main():
    """Run the MCP server."""
    # Initialize logging
    global logger
    logger = setup_mcp_logging("server")
    logger.info("Starting gitfleet MCP server")

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
