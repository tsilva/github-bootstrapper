"""Sandbox-enable operation: enable Claude Code sandbox mode in repositories."""

import os
import json
import logging
from typing import Dict, Any
from .base import Operation, OperationResult, OperationStatus
from ..utils.git import repo_exists

logger = logging.getLogger('github_bootstrapper')


class SandboxEnableOperation(Operation):
    """Sandbox-enable operation: enable Claude Code sandbox mode."""

    name = "sandbox-enable"
    description = "Enable Claude Code sandbox mode with auto-allow bash"
    requires_token = False
    safe_parallel = True

    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute sandbox-enable operation on a repository.

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
            logger.info(f"[DRY RUN] Would enable sandbox for {repo_name}")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message="Dry run: Would enable sandbox",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Enable sandbox
        try:
            # Create .claude directory if it doesn't exist
            claude_dir = os.path.join(repo_path, '.claude')
            os.makedirs(claude_dir, exist_ok=True)

            # Path to settings file
            settings_path = os.path.join(claude_dir, 'settings.local.json')

            # Read existing settings or create new
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                logger.info(f"Updating existing settings for {repo_name}")
            else:
                settings = {}
                logger.info(f"Creating new settings for {repo_name}")

            # Set sandbox configuration
            if 'sandbox' not in settings:
                settings['sandbox'] = {}

            settings['sandbox']['enabled'] = True
            settings['sandbox']['autoAllowBashIfSandboxed'] = True

            # Write settings file
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)

            logger.info(f"Enabled sandbox for {repo_name}")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message="Sandbox enabled successfully",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        except Exception as e:
            logger.error(f"Failed to enable sandbox for {repo_name}: {e}")
            return OperationResult(
                status=OperationStatus.FAILED,
                message=f"Failed to enable sandbox: {str(e)}",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

    def should_skip(self, repo: Dict[str, Any], repo_path: str) -> str:
        """Check if sandbox-enable should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            Skip reason if should skip, None otherwise
        """
        # Skip if repo doesn't exist
        if not repo_exists(repo_path):
            return "Repository doesn't exist locally"

        return None
