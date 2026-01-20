"""Git operations and utilities."""

import os
import subprocess
import logging
from typing import Optional

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
