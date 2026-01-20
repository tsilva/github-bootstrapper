"""Sync operation: clone new repos and pull updates for existing ones."""

import logging
from typing import Dict, Any
from .base import Operation, OperationResult, OperationStatus
from ..utils.git import repo_exists, has_unstaged_changes, clone_repo, pull_repo

logger = logging.getLogger('github_bootstrapper')


class SyncOperation(Operation):
    """Sync operation: clone new repositories and pull updates for existing ones."""

    name = "sync"
    description = "Clone new repos and pull updates for existing repos"
    requires_token = False
    safe_parallel = True

    def __init__(self, base_dir: str, dry_run: bool = False, clone_url_getter=None):
        """Initialize sync operation.

        Args:
            base_dir: Base directory for repositories
            dry_run: If True, don't actually execute operations
            clone_url_getter: Callable to get clone URL from repo dict
        """
        super().__init__(base_dir, dry_run)
        self.clone_url_getter = clone_url_getter

    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute sync operation on a repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            OperationResult indicating success/failure/skip
        """
        repo_name = repo['name']
        repo_full_name = repo['full_name']

        # Check if should skip
        skip_reason = self.should_skip(repo, repo_path)
        if skip_reason:
            logger.warning(f"Skipping {repo_name}: {skip_reason}")
            return OperationResult(
                status=OperationStatus.SKIPPED,
                message=skip_reason,
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Handle dry run
        if self.dry_run:
            if repo_exists(repo_path):
                action = "Would pull"
            else:
                action = "Would clone"
            logger.info(f"[DRY RUN] {action} {repo_name}")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message=f"Dry run: {action}",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Get clone URL
        if self.clone_url_getter:
            clone_url = self.clone_url_getter(repo)
        else:
            clone_url = repo.get('clone_url', repo.get('ssh_url'))

        # Execute sync
        if repo_exists(repo_path):
            # Repository exists - pull updates
            logger.info(f"Repository {repo_name} exists, pulling updates...")
            if pull_repo(repo_path):
                return OperationResult(
                    status=OperationStatus.SUCCESS,
                    message="Pulled latest changes",
                    repo_name=repo_name,
                    repo_full_name=repo_full_name
                )
            else:
                return OperationResult(
                    status=OperationStatus.FAILED,
                    message="Failed to pull changes",
                    repo_name=repo_name,
                    repo_full_name=repo_full_name
                )
        else:
            # Repository doesn't exist - clone it
            logger.info(f"Cloning {repo_name}...")
            if clone_repo(clone_url, repo_path):
                return OperationResult(
                    status=OperationStatus.SUCCESS,
                    message="Cloned successfully",
                    repo_name=repo_name,
                    repo_full_name=repo_full_name
                )
            else:
                return OperationResult(
                    status=OperationStatus.FAILED,
                    message="Failed to clone",
                    repo_name=repo_name,
                    repo_full_name=repo_full_name
                )

    def should_skip(self, repo: Dict[str, Any], repo_path: str) -> str:
        """Check if sync should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            Skip reason if should skip, None otherwise
        """
        # Skip if repo exists and has unstaged changes
        if repo_exists(repo_path) and has_unstaged_changes(repo_path):
            return "Repository has unstaged changes"
        return None
