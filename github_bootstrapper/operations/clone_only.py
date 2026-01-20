"""Clone-only operation: clone repositories that don't exist locally."""

import logging
from typing import Dict, Any
from .base import Operation, OperationResult, OperationStatus
from ..utils.git import repo_exists, clone_repo

logger = logging.getLogger('github_bootstrapper')


class CloneOnlyOperation(Operation):
    """Clone-only operation: clone repositories that don't exist locally."""

    name = "clone-only"
    description = "Clone repositories that don't exist locally"
    requires_token = False
    safe_parallel = True

    def __init__(self, base_dir: str, dry_run: bool = False, clone_url_getter=None):
        """Initialize clone-only operation.

        Args:
            base_dir: Base directory for repositories
            dry_run: If True, don't actually execute operations
            clone_url_getter: Callable to get clone URL from repo dict
        """
        super().__init__(base_dir, dry_run)
        self.clone_url_getter = clone_url_getter

    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute clone-only operation on a repository.

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
            logger.info(f"Skipping {repo_name}: {skip_reason}")
            return OperationResult(
                status=OperationStatus.SKIPPED,
                message=skip_reason,
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Handle dry run
        if self.dry_run:
            logger.info(f"[DRY RUN] Would clone {repo_name}")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message="Dry run: Would clone",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Get clone URL
        if self.clone_url_getter:
            clone_url = self.clone_url_getter(repo)
        else:
            clone_url = repo.get('clone_url', repo.get('ssh_url'))

        # Clone repository
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
        """Check if clone should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            Skip reason if should skip, None otherwise
        """
        # Skip if repo already exists
        if repo_exists(repo_path):
            return "Repository already exists locally"
        return None
