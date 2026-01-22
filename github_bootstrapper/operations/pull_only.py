"""Pull-only operation: pull updates for repositories that exist locally."""

import logging
from typing import Dict, Any
from .base import Operation, OperationResult, OperationStatus
from ..utils.git import repo_exists, has_unstaged_changes, pull_repo

logger = logging.getLogger('gitfleet')


class PullOnlyOperation(Operation):
    """Pull-only operation: pull updates for repositories that exist locally."""

    name = "pull-only"
    description = "Pull updates for repositories that exist locally"
    requires_token = False
    safe_parallel = True

    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute pull-only operation on a repository.

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
            logger.info(f"[DRY RUN] Would pull {repo_name}")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message="Dry run: Would pull",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Pull updates
        logger.info(f"Pulling updates for {repo_name}...")
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

    def should_skip(self, repo: Dict[str, Any], repo_path: str) -> str:
        """Check if pull should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            Skip reason if should skip, None otherwise
        """
        # Skip if repo doesn't exist
        if not repo_exists(repo_path):
            return "Repository doesn't exist locally"

        # Skip if repo has unstaged changes
        if has_unstaged_changes(repo_path):
            return "Repository has unstaged changes"

        return None
