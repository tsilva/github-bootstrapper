"""Git operations and utilities."""

import os
import subprocess
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger('github_bootstrapper')


def has_unstaged_changes(repo_path: str) -> bool:
    """Check if repository has unstaged changes.

    Args:
        repo_path: Path to the repository

    Returns:
        True if there are unstaged changes, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False
        )
        return bool(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True


def get_current_branch(repo_path: str) -> Optional[str]:
    """Get the current branch of the repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Branch name or None if failed
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def clone_repo(clone_url: str, repo_path: str) -> bool:
    """Clone a repository.

    Args:
        clone_url: URL to clone from
        repo_path: Local path to clone to

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Cloning to {repo_path}...")
        subprocess.run(
            ["git", "clone", clone_url, repo_path],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone: {e}")
        return False


def pull_repo(repo_path: str) -> bool:
    """Pull latest changes for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get current branch
        branch = get_current_branch(repo_path)
        if not branch:
            logger.error(f"Could not determine current branch for {repo_path}")
            return False

        logger.info(f"Pulling latest changes (branch: {branch})...")
        subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=repo_path,
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to pull: {e}")
        return False


def repo_exists(repo_path: str) -> bool:
    """Check if a repository exists locally.

    Args:
        repo_path: Path to check

    Returns:
        True if the path exists and is a directory
    """
    return os.path.exists(repo_path) and os.path.isdir(repo_path)


def get_remote_tracking_branch(repo_path: str) -> Optional[str]:
    """Get the remote tracking branch for the current branch.

    Args:
        repo_path: Path to the repository

    Returns:
        Remote tracking branch name (e.g., 'origin/main') or None if no tracking branch exists
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{upstream}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_sync_status(repo_path: str, fetch: bool = True) -> Dict[str, Any]:
    """Get the synchronization status of a repository.

    Args:
        repo_path: Path to the repository
        fetch: Whether to fetch from remote first (default True)

    Returns:
        Dictionary with keys:
        - has_remote (bool): Remote tracking branch exists
        - ahead (int): Commits ahead of remote
        - behind (int): Commits behind remote
        - has_changes (bool): Uncommitted changes exist
        - current_branch (str|None): Current branch name
        - remote_branch (str|None): Remote tracking branch
    """
    status = {
        'has_remote': False,
        'ahead': 0,
        'behind': 0,
        'has_changes': False,
        'current_branch': None,
        'remote_branch': None
    }

    # Fetch from remote if requested
    if fetch:
        try:
            subprocess.run(
                ["git", "fetch"],
                cwd=repo_path,
                capture_output=True,
                check=True,
                timeout=30
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Failed to fetch from remote: {e}")

    # Get current branch
    current_branch = get_current_branch(repo_path)
    status['current_branch'] = current_branch

    # Check for detached HEAD
    if current_branch == "HEAD":
        return status

    # Get remote tracking branch
    remote_branch = get_remote_tracking_branch(repo_path)
    status['remote_branch'] = remote_branch
    status['has_remote'] = remote_branch is not None

    # Get ahead/behind counts if we have a remote
    if remote_branch:
        try:
            # Count commits ahead
            result = subprocess.run(
                ["git", "rev-list", "--count", f"{remote_branch}..HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            status['ahead'] = int(result.stdout.strip())

            # Count commits behind
            result = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..{remote_branch}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            status['behind'] = int(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.warning(f"Failed to get ahead/behind counts: {e}")

    # Check for uncommitted changes
    status['has_changes'] = has_unstaged_changes(repo_path)

    return status
