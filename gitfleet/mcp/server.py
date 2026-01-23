"""MCP server for gitfleet using FastMCP.

This module implements the MCP server that exposes gitfleet's multi-repo
operations as tools that can be orchestrated by Claude. FastMCP provides
proper async architecture for handling concurrent requests automatically.
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Annotated

from fastmcp import FastMCP

from .tools import (
    list_repos,
    exec_command_parallel,
    exec_claude_single,
    sync_repos,
    get_status,
)
from .logging_utils import (
    setup_mcp_logging,
    get_mcp_logger,
    log_tool_invocation,
    log_summary,
)

# Logger will be configured in main()
logger = get_mcp_logger()

# Create FastMCP server
mcp = FastMCP("gitfleet")


def _ts():
    """Return current timestamp for logging."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


@mcp.tool()
async def gitfleet_list_repos(
    source: Annotated[str, "Repository source: 'github:username', 'local', or comma-separated repo names"],
    filters: Annotated[list[str], "Filter strings. Archived and forked repos are excluded by default. Use 'archived' or 'fork' to include them."] = [],
    fields: Annotated[list[str], "Fields to return (default: ['name']). Use ['all'] for all fields. Available: name, full_name, description, language, private, fork, archived, default_branch, html_url, local_path, exists_locally"] = ["name"],
    limit: Annotated[int, "Max repos to return (default: 100, max: 1000)"] = 100
) -> dict:
    """List and filter GitHub repositories using gh CLI (no token needed).

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
- "public" - only public repos"""
    log_tool_invocation("gitfleet_list_repos", {"source": source, "filters": filters}, logger)
    start_time = time.time()

    result = await asyncio.to_thread(
        list_repos,
        source=source,
        filters=filters,
        fields=fields,
        limit=limit
    )

    output = {
        "count": len(result),
        "repos": [r.to_dict(fields) for r in result]
    }

    duration_ms = int((time.time() - start_time) * 1000)
    log_summary(
        "gitfleet_list_repos", total=len(result), success=len(result),
        failed=0, skipped=0, duration_ms=duration_ms, logger=logger
    )

    return output


@mcp.tool()
async def gitfleet_exec(
    repos: Annotated[list[str], "List of repository names to execute on"],
    command: Annotated[str, "Command to execute (with optional prefix: gh:, git:)"],
    dry_run: Annotated[bool, "Preview without executing (default: false)"] = False,
    timeout: Annotated[int, "Timeout in seconds per repo (default: 60)"] = 60,
    max_workers: Annotated[int, "Maximum parallel workers (default: 8)"] = 8
) -> dict:
    """Execute commands across multiple repositories in PARALLEL.

This tool runs git, gh, and shell commands with parallel execution for fast multi-repo operations.

Command prefixes:
- "gh:" - Run GitHub CLI command (e.g., "gh:pr list")
- "git:" - Run git command (e.g., "git:status")
- No prefix - Run shell command (e.g., "npm install")

NOTE: Claude commands are NOT supported by this tool. Use gitfleet_claude_exec instead,
which takes a single repo and allows caller-side parallelization via multiple MCP calls.

Examples:
- Run git command: repos=["repo-a", "repo-b"], command="git:status"
- Run gh command: repos=["repo-a", "repo-b"], command="gh:pr list"
- Run shell command: repos=["repo-a"], command="npm install"

The tool returns structured results showing which repos succeeded, failed, or were skipped."""
    log_tool_invocation("gitfleet_exec", {"repos": repos, "command": command}, logger)
    start_time = time.time()

    result = await asyncio.to_thread(
        exec_command_parallel,
        repos=repos,
        command=command,
        dry_run=dry_run,
        timeout=timeout,
        max_workers=max_workers
    )

    output = result.to_dict()
    duration_ms = int((time.time() - start_time) * 1000)
    log_summary(
        "gitfleet_exec", total=result.total, success=len(result.success),
        failed=len(result.failed), skipped=len(result.skipped),
        duration_ms=duration_ms, logger=logger
    )

    return output


@mcp.tool()
async def gitfleet_claude_exec_batch(
    repos: Annotated[list[str], "List of repository names"],
    prompt: Annotated[str, "Claude prompt or skill to execute on ALL repos"],
    dry_run: Annotated[bool, "Preview without executing (default: false)"] = False,
    timeout: Annotated[int, "Timeout in seconds per repo (default: 300)"] = 300,
    max_workers: Annotated[int, "Maximum parallel workers (default: 4)"] = 4
) -> dict:
    """Execute a Claude prompt on MULTIPLE repositories in PARALLEL.

Use this for batch operations across repos. The server handles parallelization internally.

Examples:
- repos=["repo-a", "repo-b"], prompt="/readme-generator"
- repos=["repo-a", "repo-b", "repo-c"], prompt="Add MIT LICENSE file"

Returns aggregated results with success/failed/skipped lists."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    logger.info(f"[{_ts()}] START gitfleet_claude_exec_batch repos={repos} workers={max_workers}")
    log_tool_invocation("gitfleet_claude_exec_batch", {"repos": repos, "prompt": prompt[:80]}, logger)
    start_time = time.time()

    results = {"success": [], "failed": [], "skipped": [], "total": len(repos)}

    def run_single(repo: str) -> dict:
        tid = threading.get_ident()
        logger.info(f"[{_ts()}] WORKER_START repo={repo} thread={tid}")
        result = exec_claude_single(repo=repo, prompt=prompt, dry_run=dry_run, timeout=timeout)
        logger.info(f"[{_ts()}] WORKER_END repo={repo} status={result.status}")
        return result.to_dict()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_repo = {executor.submit(run_single, repo): repo for repo in repos}
        for future in as_completed(future_to_repo):
            repo = future_to_repo[future]
            try:
                result = future.result()
                if result["status"] == "success":
                    results["success"].append(repo)
                elif result["status"] == "skipped":
                    results["skipped"].append(repo)
                else:
                    results["failed"].append({"repo": repo, "error": result.get("error")})
            except Exception as e:
                results["failed"].append({"repo": repo, "error": str(e)})

    duration_ms = int((time.time() - start_time) * 1000)
    log_summary(
        "gitfleet_claude_exec_batch", total=len(repos), success=len(results["success"]),
        failed=len(results["failed"]), skipped=len(results["skipped"]),
        duration_ms=duration_ms, logger=logger
    )
    logger.info(f"[{_ts()}] END gitfleet_claude_exec_batch duration={duration_ms}ms")

    return results


@mcp.tool()
async def gitfleet_claude_exec(
    repo: Annotated[str, "Single repository name"],
    prompt: Annotated[str, "Claude prompt or skill (e.g., 'Add tests' or '/readme-generator')"],
    dry_run: Annotated[bool, "Preview without executing (default: false)"] = False,
    timeout: Annotated[int, "Timeout in seconds (default: 300)"] = 300
) -> dict:
    """Execute a Claude prompt or skill on a SINGLE repository.

For multi-repo Claude operations, invoke this tool multiple times in parallel.
This design avoids rate limit issues from internal parallelization.

Command formats:
- Raw prompt: "Add a LICENSE file"
- Skill invocation: "/readme-generator"

Examples:
- repo="my-repo", prompt="/readme-generator"
- repo="my-repo", prompt="Add comprehensive docstrings"

Returns success/failure with Claude's output."""
    tid = threading.get_ident()
    logger.info(f"[{_ts()}] START gitfleet_claude_exec repo={repo} thread={tid}")
    log_tool_invocation("gitfleet_claude_exec", {"repo": repo, "prompt": prompt[:80]}, logger)
    start_time = time.time()

    def _run_claude():
        inner_tid = threading.get_ident()
        logger.info(f"[{_ts()}] IN_THREAD exec_claude_single repo={repo} thread={inner_tid}")
        return exec_claude_single(repo=repo, prompt=prompt, dry_run=dry_run, timeout=timeout)

    logger.info(f"[{_ts()}] BEFORE asyncio.to_thread repo={repo}")
    result = await asyncio.to_thread(_run_claude)
    logger.info(f"[{_ts()}] AFTER asyncio.to_thread repo={repo}")

    output = result.to_dict()
    duration_ms = int((time.time() - start_time) * 1000)
    success_count = 1 if result.status == "success" else 0
    failed_count = 1 if result.status == "failed" else 0
    skipped_count = 1 if result.status == "skipped" else 0
    log_summary(
        "gitfleet_claude_exec", total=1, success=success_count,
        failed=failed_count, skipped=skipped_count,
        duration_ms=duration_ms, logger=logger
    )

    logger.info(f"[{_ts()}] END gitfleet_claude_exec repo={repo}")
    return output


@mcp.tool()
async def gitfleet_sync(
    repos: Annotated[list[str], "List of repository names to sync"],
    operation: Annotated[str, "Sync operation type: 'sync', 'clone', or 'pull' (default: sync)"] = "sync"
) -> dict:
    """Sync repositories by cloning new repos and/or pulling updates.

Operations:
- "sync" (default): Clone missing repos AND pull updates for existing ones
- "clone": Only clone repos that don't exist locally
- "pull": Only pull updates for repos that exist locally

Repos with uncommitted changes are skipped during pull to prevent data loss.

Example: repos=["repo-a", "repo-b"], operation="sync" """
    log_tool_invocation("gitfleet_sync", {"repos": repos, "operation": operation}, logger)
    start_time = time.time()

    result = await asyncio.to_thread(
        sync_repos,
        repos=repos,
        operation=operation
    )

    output = result.to_dict()
    duration_ms = int((time.time() - start_time) * 1000)
    total = len(result.cloned) + len(result.pulled) + len(result.skipped) + len(result.failed)
    log_summary(
        "gitfleet_sync", total=total, success=len(result.cloned) + len(result.pulled),
        failed=len(result.failed), skipped=len(result.skipped),
        duration_ms=duration_ms, logger=logger
    )

    return output


@mcp.tool()
async def gitfleet_status(
    repos: Annotated[list[str], "List of repository names to check"]
) -> dict:
    """Get synchronization status of repositories.

Returns repos categorized by their status:
- in_sync: Up to date with remote
- unpushed: Local commits not pushed
- unpulled: Remote commits not pulled
- diverged: Both local and remote have new commits
- uncommitted: Has uncommitted changes
- detached: HEAD is detached
- no_remote: No remote tracking branch
- not_cloned: Repository not cloned locally

Use this to understand the state of repos before running operations."""
    log_tool_invocation("gitfleet_status", {"repos": repos}, logger)
    start_time = time.time()

    result = await asyncio.to_thread(get_status, repos=repos)

    output = result.to_dict()
    duration_ms = int((time.time() - start_time) * 1000)
    log_summary(
        "gitfleet_status", total=result.total, success=result.total,
        failed=0, skipped=0, duration_ms=duration_ms, logger=logger
    )

    return output


def main():
    """Run the MCP server."""
    global logger
    logger = setup_mcp_logging("server")
    logger.info("Starting gitfleet MCP server (FastMCP)")
    mcp.run()


if __name__ == "__main__":
    main()
