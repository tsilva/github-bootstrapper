"""MCP tool implementations for gitfleet.

This module contains the actual implementations of the MCP tools:
- gitfleet_list_repos: List and filter repositories
- gitfleet_exec: Execute commands across repos (including Claude prompts)
- gitfleet_sync: Sync repositories (clone/pull)
- gitfleet_status: Get repository status

All GitHub operations use the `gh` CLI which handles authentication automatically.
"""

import os
import subprocess
import json
import fnmatch
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .logging_utils import get_mcp_logger, log_repo_result, timed_operation

logger = get_mcp_logger()


# ============================================================================
# Data types for tool responses
# ============================================================================

@dataclass
class RepoInfo:
    """Repository information returned by list_repos."""
    name: str
    full_name: str
    description: Optional[str]
    language: Optional[str]
    private: bool
    fork: bool
    archived: bool
    default_branch: str
    html_url: str
    local_path: Optional[str] = None
    exists_locally: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecRepoResult:
    """Result for a single repo in exec operation."""
    repo: str
    status: str  # "success", "failed", "skipped"
    output: Optional[str] = None
    error: Optional[str] = None
    return_code: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionResult:
    """Result of gitfleet_exec operation."""
    success: List[str] = field(default_factory=list)
    failed: List[ExecRepoResult] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "failed": [r.to_dict() for r in self.failed],
            "skipped": self.skipped,
            "total": self.total
        }


@dataclass
class SyncRepoResult:
    """Result for a single repo in sync operation."""
    repo: str
    status: str  # "cloned", "pulled", "skipped", "failed"
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SyncResult:
    """Result of gitfleet_sync operation."""
    cloned: List[str] = field(default_factory=list)
    pulled: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    failed: List[SyncRepoResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cloned": self.cloned,
            "pulled": self.pulled,
            "skipped": self.skipped,
            "failed": [r.to_dict() for r in self.failed]
        }


@dataclass
class RepoStatus:
    """Status of a single repository."""
    repo: str
    category: str
    details: Optional[str] = None
    ahead: int = 0
    behind: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StatusSummary:
    """Summary of repository statuses."""
    total: int = 0
    in_sync: List[str] = field(default_factory=list)
    unpushed: List[RepoStatus] = field(default_factory=list)
    unpulled: List[RepoStatus] = field(default_factory=list)
    diverged: List[RepoStatus] = field(default_factory=list)
    uncommitted: List[str] = field(default_factory=list)
    detached: List[str] = field(default_factory=list)
    no_remote: List[str] = field(default_factory=list)
    not_cloned: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "in_sync": self.in_sync,
            "unpushed": [r.to_dict() for r in self.unpushed],
            "unpulled": [r.to_dict() for r in self.unpulled],
            "diverged": [r.to_dict() for r in self.diverged],
            "uncommitted": self.uncommitted,
            "detached": self.detached,
            "no_remote": self.no_remote,
            "not_cloned": self.not_cloned
        }


# ============================================================================
# Helper functions
# ============================================================================

def _get_base_dir() -> str:
    """Get base directory for repositories."""
    return os.getcwd()


def _gh_repo_list(owner: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
    """List repositories using gh CLI.

    Args:
        owner: GitHub username or org (None = authenticated user)
        limit: Maximum number of repos to return

    Returns:
        List of repository dictionaries
    """
    cmd = ["gh", "repo", "list"]
    if owner:
        cmd.append(owner)
    cmd.extend([
        "--limit", str(limit),
        "--json", "name,nameWithOwner,description,primaryLanguage,isPrivate,isFork,isArchived,defaultBranchRef,url"
    ])

    logger.debug(f"Executing: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            logger.error(f"gh repo list failed: {result.stderr}")
            return []

        repos = json.loads(result.stdout)
        # Normalize the data structure
        normalized = []
        for repo in repos:
            normalized.append({
                "name": repo.get("name"),
                "full_name": repo.get("nameWithOwner"),
                "description": repo.get("description"),
                "language": repo.get("primaryLanguage", {}).get("name") if repo.get("primaryLanguage") else None,
                "private": repo.get("isPrivate", False),
                "fork": repo.get("isFork", False),
                "archived": repo.get("isArchived", False),
                "default_branch": repo.get("defaultBranchRef", {}).get("name", "main") if repo.get("defaultBranchRef") else "main",
                "html_url": repo.get("url", "")
            })

        logger.info(f"gh repo list returned {len(normalized)} repositories")
        return normalized

    except subprocess.TimeoutExpired:
        logger.error("gh repo list timed out after 60s")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse gh output: {e}")
        return []
    except FileNotFoundError:
        logger.error("gh CLI not found - ensure GitHub CLI is installed")
        return []


def _gh_get_authenticated_user() -> Optional[str]:
    """Get the authenticated GitHub username.

    Returns:
        Username or None if not authenticated
    """
    logger.debug("Checking gh authentication status")
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            username = result.stdout.strip()
            logger.debug(f"Authenticated as: {username}")
            return username
        logger.debug("Not authenticated with gh CLI")
    except subprocess.TimeoutExpired:
        logger.debug("gh auth check timed out")
    except FileNotFoundError:
        logger.debug("gh CLI not found")
    return None


def _parse_filters(filters: List[str]) -> Dict[str, Any]:
    """Parse filter strings into filter parameters.

    Supported filters:
    - "!archived" - exclude archived repos
    - "!fork" - exclude forked repos
    - "language:python" - filter by language
    - "owner:myorg" - filter by owner
    - "pattern:my-*" - filter by glob pattern
    - "private" - only private repos
    - "public" - only public repos

    Args:
        filters: List of filter strings

    Returns:
        Dictionary of filter parameters
    """
    result = {
        "include_archived": True,
        "include_forks": True,
        "language": None,
        "owner": None,
        "pattern": None,
        "private_only": False,
        "public_only": False
    }

    for f in filters:
        if f == "!archived":
            result["include_archived"] = False
        elif f == "!fork":
            result["include_forks"] = False
        elif f.startswith("language:"):
            result["language"] = f[9:]
        elif f.startswith("owner:"):
            result["owner"] = f[6:]
        elif f.startswith("pattern:"):
            result["pattern"] = f[8:]
        elif f == "private":
            result["private_only"] = True
        elif f == "public":
            result["public_only"] = True

    logger.debug(f"Parsed filters {filters} -> {result}")
    return result


def _apply_filters(repos: List[Dict[str, Any]], filter_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply filters to a list of repositories."""
    original_count = len(repos)
    filtered = []

    for repo in repos:
        # Check archived
        if not filter_params["include_archived"] and repo.get("archived", False):
            continue

        # Check fork
        if not filter_params["include_forks"] and repo.get("fork", False):
            continue

        # Check language
        if filter_params["language"]:
            repo_lang = (repo.get("language") or "").lower()
            if repo_lang != filter_params["language"].lower():
                continue

        # Check owner
        if filter_params["owner"]:
            full_name = repo.get("full_name", "")
            owner = full_name.split("/")[0] if "/" in full_name else ""
            if owner != filter_params["owner"]:
                continue

        # Check pattern
        if filter_params["pattern"]:
            if not fnmatch.fnmatch(repo["name"], filter_params["pattern"]):
                continue

        # Check visibility
        is_private = repo.get("private", False)
        if filter_params["private_only"] and not is_private:
            continue
        if filter_params["public_only"] and is_private:
            continue

        filtered.append(repo)

    logger.info(f"Filtered {original_count} repos to {len(filtered)}")
    return filtered


def _scan_local_repos(base_dir: str) -> List[str]:
    """Scan directory for local git repositories."""
    logger.debug(f"Scanning for local repos in: {base_dir}")
    repos = []
    try:
        for entry in os.scandir(base_dir):
            if entry.is_dir() and not entry.name.startswith('.'):
                git_dir = os.path.join(entry.path, '.git')
                if os.path.isdir(git_dir):
                    repos.append(entry.name)
    except OSError as e:
        logger.error(f"Error scanning directory {base_dir}: {e}")
    result = sorted(repos)
    logger.info(f"Found {len(result)} local repositories")
    return result


def _repo_exists(repo_path: str) -> bool:
    """Check if a repository exists locally."""
    return os.path.isdir(os.path.join(repo_path, '.git'))


def _get_sync_status(repo_path: str, fetch: bool = True) -> Dict[str, Any]:
    """Get synchronization status for a repository."""
    repo_name = os.path.basename(repo_path)
    logger.debug(f"Getting sync status for {repo_name} (fetch={fetch})")

    result = {
        "current_branch": None,
        "has_remote": False,
        "ahead": 0,
        "behind": 0,
        "has_changes": False
    }

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        if branch_result.returncode != 0:
            logger.debug(f"{repo_name}: Failed to get current branch")
            return result

        result["current_branch"] = branch_result.stdout.strip()

        # Check for uncommitted changes
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        result["has_changes"] = bool(status_result.stdout.strip())

        # Fetch from remote if requested
        if fetch:
            logger.debug(f"{repo_name}: Fetching from remote")
            subprocess.run(
                ["git", "fetch"],
                cwd=repo_path,
                capture_output=True,
                timeout=60
            )

        # Check remote tracking
        tracking_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{upstream}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        if tracking_result.returncode != 0:
            logger.debug(f"{repo_name}: No remote tracking branch")
            return result

        result["has_remote"] = True

        # Get ahead/behind counts
        rev_list = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        if rev_list.returncode == 0:
            parts = rev_list.stdout.strip().split()
            if len(parts) == 2:
                result["ahead"] = int(parts[0])
                result["behind"] = int(parts[1])

        logger.debug(f"{repo_name}: branch={result['current_branch']}, ahead={result['ahead']}, behind={result['behind']}, changes={result['has_changes']}")

    except subprocess.TimeoutExpired:
        logger.debug(f"{repo_name}: Git operation timed out")
    except (subprocess.SubprocessError, ValueError) as e:
        logger.debug(f"{repo_name}: Error getting status: {e}")

    return result


# ============================================================================
# Tool implementations
# ============================================================================

def list_repos(
    source: str,
    filters: Optional[List[str]] = None
) -> List[RepoInfo]:
    """List repositories based on source and filters.

    Args:
        source: Repository source - "github", "github:owner", "local", or comma-separated repo names
        filters: Optional list of filters like ["!archived", "!fork", "language:python"]

    Returns:
        List of RepoInfo objects
    """
    logger.info(f"list_repos: source={source}, filters={filters}")

    filters = filters or []
    filter_params = _parse_filters(filters)
    base_dir = _get_base_dir()

    repos = []

    if source == "github" or source.startswith("github:"):
        # Extract owner if provided
        owner = source[7:] if source.startswith("github:") else None

        # Get repos via gh CLI
        github_repos = _gh_repo_list(owner)
        github_repos = _apply_filters(github_repos, filter_params)

        for repo in github_repos:
            local_path = os.path.join(base_dir, repo['name'])
            repos.append(RepoInfo(
                name=repo['name'],
                full_name=repo['full_name'],
                description=repo.get('description'),
                language=repo.get('language'),
                private=repo.get('private', False),
                fork=repo.get('fork', False),
                archived=repo.get('archived', False),
                default_branch=repo.get('default_branch', 'main'),
                html_url=repo.get('html_url', ''),
                local_path=local_path,
                exists_locally=_repo_exists(local_path)
            ))

    elif source == "local":
        # Scan local repos
        local_repo_names = _scan_local_repos(base_dir)

        # Try to enrich with GitHub data
        github_repos = {r['name']: r for r in _gh_repo_list()}

        for name in local_repo_names:
            local_path = os.path.join(base_dir, name)
            github_data = github_repos.get(name, {})

            # Apply filters if we have GitHub data
            if github_data:
                if not filter_params["include_archived"] and github_data.get("archived", False):
                    continue
                if not filter_params["include_forks"] and github_data.get("fork", False):
                    continue
                if filter_params["language"]:
                    repo_lang = (github_data.get("language") or "").lower()
                    if repo_lang != filter_params["language"].lower():
                        continue
                if filter_params["private_only"] and not github_data.get("private", False):
                    continue
                if filter_params["public_only"] and github_data.get("private", False):
                    continue

            if filter_params["pattern"]:
                if not fnmatch.fnmatch(name, filter_params["pattern"]):
                    continue

            repos.append(RepoInfo(
                name=name,
                full_name=github_data.get('full_name', name),
                description=github_data.get('description'),
                language=github_data.get('language'),
                private=github_data.get('private', False),
                fork=github_data.get('fork', False),
                archived=github_data.get('archived', False),
                default_branch=github_data.get('default_branch', 'main'),
                html_url=github_data.get('html_url', ''),
                local_path=local_path,
                exists_locally=True
            ))

    else:
        # Specific repo names (comma-separated)
        repo_names = [r.strip() for r in source.split(',') if r.strip()]

        # Try to get GitHub data
        github_repos = {r['name']: r for r in _gh_repo_list()}

        for name in repo_names:
            local_path = os.path.join(base_dir, name)
            github_data = github_repos.get(name, {})

            repos.append(RepoInfo(
                name=name,
                full_name=github_data.get('full_name', name),
                description=github_data.get('description'),
                language=github_data.get('language'),
                private=github_data.get('private', False),
                fork=github_data.get('fork', False),
                archived=github_data.get('archived', False),
                default_branch=github_data.get('default_branch', 'main'),
                html_url=github_data.get('html_url', ''),
                local_path=local_path,
                exists_locally=_repo_exists(local_path)
            ))

    local_count = sum(1 for r in repos if r.exists_locally)
    logger.info(f"list_repos: returning {len(repos)} repos ({local_count} exist locally)")
    return repos


def exec_command(
    repos: List[str],
    command: str,
    parallel: bool = True,
    workers: int = 4,
    dry_run: bool = False,
    timeout: int = 300
) -> ExecutionResult:
    """Execute a command across multiple repositories.

    The command can be:
    - Shell command: "npm install", "git status"
    - Claude prompt: "claude:Add a LICENSE file"
    - Claude skill: "claude:/readme-generator"
    - GitHub CLI: "gh:pr list"
    - Git command: "git:status"

    Args:
        repos: List of repository names or paths
        command: Command to execute (with optional prefix)
        parallel: Whether to execute in parallel
        workers: Number of parallel workers
        dry_run: Preview without executing
        timeout: Timeout in seconds per repo

    Returns:
        ExecutionResult with success/failed/skipped repos
    """
    base_dir = _get_base_dir()
    result = ExecutionResult(total=len(repos))

    # Parse command prefix
    cmd_type = "shell"
    cmd_value = command

    if command.startswith("claude:"):
        cmd_type = "claude"
        cmd_value = command[7:]
    elif command.startswith("gh:"):
        cmd_type = "gh"
        cmd_value = command[3:]
    elif command.startswith("git:"):
        cmd_type = "git"
        cmd_value = command[4:]

    mode = "parallel" if parallel and len(repos) > 1 else "sequential"
    logger.info(f"exec_command: {len(repos)} repos, type={cmd_type}, mode={mode}, dry_run={dry_run}")

    def execute_on_repo(repo_name: str) -> ExecRepoResult:
        """Execute command on a single repository."""
        repo_path = os.path.join(base_dir, repo_name)
        logger.debug(f"exec_command: processing {repo_name}")

        # Check if repo exists
        if not _repo_exists(repo_path):
            log_repo_result(repo_name, "skipped", "Not cloned locally")
            return ExecRepoResult(
                repo=repo_name,
                status="skipped",
                error="Repository not cloned locally"
            )

        if dry_run:
            log_repo_result(repo_name, "success", f"[DRY RUN] {command}")
            return ExecRepoResult(
                repo=repo_name,
                status="success",
                output=f"[DRY RUN] Would execute: {command}"
            )

        try:
            if cmd_type == "claude":
                # Execute Claude CLI
                cmd = [
                    "claude",
                    "-p", cmd_value,
                    "--permission-mode", "acceptEdits",
                    "--output-format", "json"
                ]
            elif cmd_type == "gh":
                cmd = ["gh"] + cmd_value.split()
            elif cmd_type == "git":
                cmd = ["git"] + cmd_value.split()
            else:
                # Shell command - use shell=True for complex commands
                cmd = cmd_value

            logger.debug(f"{repo_name}: executing {cmd}")

            proc_result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=isinstance(cmd, str)
            )

            if proc_result.returncode == 0:
                log_repo_result(repo_name, "success", "Command completed")
                return ExecRepoResult(
                    repo=repo_name,
                    status="success",
                    output=proc_result.stdout[:5000] if proc_result.stdout else None,
                    return_code=proc_result.returncode
                )
            else:
                log_repo_result(repo_name, "failed", f"Exit code {proc_result.returncode}")
                return ExecRepoResult(
                    repo=repo_name,
                    status="failed",
                    output=proc_result.stdout[:2000] if proc_result.stdout else None,
                    error=proc_result.stderr[:2000] if proc_result.stderr else "Command failed",
                    return_code=proc_result.returncode
                )

        except subprocess.TimeoutExpired:
            log_repo_result(repo_name, "failed", f"Timed out after {timeout}s")
            return ExecRepoResult(
                repo=repo_name,
                status="failed",
                error=f"Command timed out after {timeout}s"
            )
        except FileNotFoundError as e:
            log_repo_result(repo_name, "failed", f"Command not found: {e}")
            return ExecRepoResult(
                repo=repo_name,
                status="failed",
                error=f"Command not found: {e}"
            )
        except Exception as e:
            log_repo_result(repo_name, "failed", str(e))
            return ExecRepoResult(
                repo=repo_name,
                status="failed",
                error=str(e)
            )

    # Execute
    if parallel and len(repos) > 1:
        with ThreadPoolExecutor(max_workers=min(workers, len(repos))) as executor:
            futures = {executor.submit(execute_on_repo, repo): repo for repo in repos}
            for future in as_completed(futures):
                repo_result = future.result()
                if repo_result.status == "success":
                    result.success.append(repo_result.repo)
                elif repo_result.status == "skipped":
                    result.skipped.append(repo_result.repo)
                else:
                    result.failed.append(repo_result)
    else:
        for repo in repos:
            repo_result = execute_on_repo(repo)
            if repo_result.status == "success":
                result.success.append(repo_result.repo)
            elif repo_result.status == "skipped":
                result.skipped.append(repo_result.repo)
            else:
                result.failed.append(repo_result)

    return result


def sync_repos(
    repos: List[str],
    operation: str = "sync"
) -> SyncResult:
    """Sync repositories (clone/pull).

    Args:
        repos: List of repository names
        operation: "sync" (clone+pull), "clone" (clone only), "pull" (pull only)

    Returns:
        SyncResult with cloned/pulled/skipped/failed repos
    """
    logger.info(f"sync_repos: {len(repos)} repos, operation={operation}")

    base_dir = _get_base_dir()
    result = SyncResult()

    # Get GitHub repo data for clone operations
    github_repos = {r['name']: r for r in _gh_repo_list()}

    def sync_repo(repo_name: str) -> SyncRepoResult:
        """Sync a single repository."""
        repo_path = os.path.join(base_dir, repo_name)
        exists = _repo_exists(repo_path)
        logger.debug(f"sync_repos: processing {repo_name} (exists={exists})")

        # Clone if needed
        if not exists:
            if operation == "pull":
                log_repo_result(repo_name, "skipped", "Not cloned, pull-only mode")
                return SyncRepoResult(
                    repo=repo_name,
                    status="skipped",
                    message="Not cloned, pull-only mode"
                )

            github_data = github_repos.get(repo_name)
            if not github_data:
                log_repo_result(repo_name, "failed", "Not found on GitHub")
                return SyncRepoResult(
                    repo=repo_name,
                    status="failed",
                    message="Repository not found on GitHub"
                )

            try:
                logger.debug(f"{repo_name}: cloning from {github_data['full_name']}")
                # Use gh repo clone which handles auth automatically
                proc = subprocess.run(
                    ["gh", "repo", "clone", github_data['full_name'], repo_path],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if proc.returncode == 0:
                    log_repo_result(repo_name, "success", "Cloned")
                    return SyncRepoResult(
                        repo=repo_name,
                        status="cloned",
                        message="Successfully cloned"
                    )
                else:
                    log_repo_result(repo_name, "failed", "Clone failed")
                    return SyncRepoResult(
                        repo=repo_name,
                        status="failed",
                        message=f"Clone failed: {proc.stderr}"
                    )
            except subprocess.TimeoutExpired:
                log_repo_result(repo_name, "failed", "Clone timed out")
                return SyncRepoResult(
                    repo=repo_name,
                    status="failed",
                    message="Clone timed out"
                )
            except Exception as e:
                log_repo_result(repo_name, "failed", f"Clone error: {e}")
                return SyncRepoResult(
                    repo=repo_name,
                    status="failed",
                    message=f"Clone error: {e}"
                )

        # Pull if exists
        if operation == "clone":
            log_repo_result(repo_name, "skipped", "Already cloned, clone-only mode")
            return SyncRepoResult(
                repo=repo_name,
                status="skipped",
                message="Already cloned, clone-only mode"
            )

        # Check for uncommitted changes
        status = _get_sync_status(repo_path, fetch=False)
        if status.get('has_changes'):
            log_repo_result(repo_name, "skipped", "Has uncommitted changes")
            return SyncRepoResult(
                repo=repo_name,
                status="skipped",
                message="Has uncommitted changes"
            )

        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"

            logger.debug(f"{repo_name}: pulling origin/{branch}")
            # Pull
            proc = subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120
            )

            if proc.returncode == 0:
                log_repo_result(repo_name, "success", "Pulled")
                return SyncRepoResult(
                    repo=repo_name,
                    status="pulled",
                    message="Successfully pulled"
                )
            else:
                log_repo_result(repo_name, "failed", "Pull failed")
                return SyncRepoResult(
                    repo=repo_name,
                    status="failed",
                    message=f"Pull failed: {proc.stderr}"
                )

        except subprocess.TimeoutExpired:
            log_repo_result(repo_name, "failed", "Pull timed out")
            return SyncRepoResult(
                repo=repo_name,
                status="failed",
                message="Pull timed out"
            )
        except Exception as e:
            log_repo_result(repo_name, "failed", f"Pull error: {e}")
            return SyncRepoResult(
                repo=repo_name,
                status="failed",
                message=f"Pull error: {e}"
            )

    # Execute sync
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(sync_repo, repo): repo for repo in repos}
        for future in as_completed(futures):
            repo_result = future.result()
            if repo_result.status == "cloned":
                result.cloned.append(repo_result.repo)
            elif repo_result.status == "pulled":
                result.pulled.append(repo_result.repo)
            elif repo_result.status == "skipped":
                result.skipped.append(repo_result.repo)
            else:
                result.failed.append(repo_result)

    return result


def get_status(repos: List[str]) -> StatusSummary:
    """Get status of repositories.

    Args:
        repos: List of repository names

    Returns:
        StatusSummary with categorized repositories
    """
    logger.info(f"get_status: checking {len(repos)} repositories")

    base_dir = _get_base_dir()
    summary = StatusSummary(total=len(repos))
    lock = threading.Lock()

    def check_repo(repo_name: str) -> None:
        """Check status of a single repository."""
        repo_path = os.path.join(base_dir, repo_name)
        logger.debug(f"get_status: checking {repo_name}")

        if not _repo_exists(repo_path):
            with lock:
                summary.not_cloned.append(repo_name)
            return

        status = _get_sync_status(repo_path, fetch=True)

        if status['current_branch'] == "HEAD":
            with lock:
                summary.detached.append(repo_name)
            return

        if not status['has_remote']:
            with lock:
                summary.no_remote.append(repo_name)
            return

        if status['has_changes']:
            with lock:
                summary.uncommitted.append(repo_name)
        elif status['behind'] > 0 and status['ahead'] > 0:
            with lock:
                summary.diverged.append(RepoStatus(
                    repo=repo_name,
                    category="diverged",
                    ahead=status['ahead'],
                    behind=status['behind']
                ))
        elif status['behind'] > 0:
            with lock:
                summary.unpulled.append(RepoStatus(
                    repo=repo_name,
                    category="unpulled",
                    behind=status['behind']
                ))
        elif status['ahead'] > 0:
            with lock:
                summary.unpushed.append(RepoStatus(
                    repo=repo_name,
                    category="unpushed",
                    ahead=status['ahead']
                ))
        else:
            with lock:
                summary.in_sync.append(repo_name)

    # Execute checks in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(check_repo, repo) for repo in repos]
        for future in as_completed(futures):
            future.result()  # Raise any exceptions

    logger.info(
        f"get_status: in_sync={len(summary.in_sync)}, uncommitted={len(summary.uncommitted)}, "
        f"unpushed={len(summary.unpushed)}, unpulled={len(summary.unpulled)}, "
        f"diverged={len(summary.diverged)}, not_cloned={len(summary.not_cloned)}"
    )
    return summary
