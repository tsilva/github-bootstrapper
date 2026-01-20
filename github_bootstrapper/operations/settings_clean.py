"""Settings-clean operation: analyze and clean Claude Code settings."""

import os
import subprocess
import logging
from typing import Dict, Any
from .base import Operation, OperationResult, OperationStatus
from ..utils.git import repo_exists

logger = logging.getLogger('github_bootstrapper')


class SettingsCleanOperation(Operation):
    """Settings-clean operation: analyze and clean Claude Code settings."""

    name = "settings-clean"
    description = "Analyze and clean Claude Code permission settings"
    requires_token = False
    safe_parallel = True

    def __init__(
        self,
        base_dir: str,
        dry_run: bool = False,
        mode: str = "analyze"
    ):
        """Initialize settings-clean operation.

        Args:
            base_dir: Base directory for repositories
            dry_run: If True, don't actually execute operations
            mode: Operation mode (analyze, clean, auto-fix)
        """
        super().__init__(base_dir, dry_run)
        self.mode = mode

        # Validate mode
        if self.mode not in ('analyze', 'clean', 'auto-fix'):
            raise ValueError(f"Invalid mode: {mode}. Must be analyze, clean, or auto-fix")

        # Locate settings-cleaner script
        self.script_path = self._find_settings_cleaner_script()

    def _find_settings_cleaner_script(self) -> str:
        """Find the settings-cleaner script.

        Returns:
            Path to settings_cleaner.py script

        Raises:
            FileNotFoundError: If script not found
        """
        # Try common locations
        home_dir = os.path.expanduser('~')
        possible_paths = [
            os.path.join(
                home_dir,
                '.claude/plugins/cache/claude-skills/settings-cleaner/1.0.4/scripts/settings_cleaner.py'
            ),
            # Try finding any version
            os.path.join(
                home_dir,
                '.claude/plugins/cache/claude-skills/settings-cleaner'
            )
        ]

        for path in possible_paths:
            if os.path.exists(path):
                if os.path.isfile(path):
                    return path
                # If directory, search for script
                for root, dirs, files in os.walk(path):
                    if 'settings_cleaner.py' in files:
                        return os.path.join(root, 'settings_cleaner.py')

        raise FileNotFoundError(
            "settings-cleaner script not found. "
            "Please install the settings-cleaner skill first."
        )

    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute settings-clean operation on a repository.

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
            logger.info(f"[DRY RUN] Would clean settings for {repo_name} (mode: {self.mode})")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message=f"Dry run: Would clean settings (mode: {self.mode})",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Run settings cleaner
        try:
            settings_path = os.path.join(repo_path, '.claude', 'settings.local.json')

            # Build command
            cmd = [
                'uv', 'run',
                '--with', 'colorama',
                self.script_path,
                self.mode,
                '--project-settings', settings_path
            ]

            logger.info(f"Running settings-cleaner for {repo_name} (mode: {self.mode})")

            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Parse output for statistics if available
                output = result.stdout
                logger.info(f"Settings cleaned for {repo_name}")
                if output:
                    logger.debug(f"Output: {output}")

                return OperationResult(
                    status=OperationStatus.SUCCESS,
                    message=f"Settings cleaned (mode: {self.mode})",
                    repo_name=repo_name,
                    repo_full_name=repo_full_name
                )
            else:
                error = result.stderr or result.stdout
                logger.error(f"Failed to clean settings for {repo_name}: {error}")
                return OperationResult(
                    status=OperationStatus.FAILED,
                    message=f"Script failed: {error[:100]}",
                    repo_name=repo_name,
                    repo_full_name=repo_full_name
                )

        except subprocess.TimeoutExpired:
            logger.error(f"Settings cleaner timed out for {repo_name}")
            return OperationResult(
                status=OperationStatus.FAILED,
                message="Operation timed out",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )
        except Exception as e:
            logger.error(f"Failed to clean settings for {repo_name}: {e}")
            return OperationResult(
                status=OperationStatus.FAILED,
                message=f"Unexpected error: {str(e)}",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

    def should_skip(self, repo: Dict[str, Any], repo_path: str) -> str:
        """Check if settings-clean should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            Skip reason if should skip, None otherwise
        """
        # Skip if repo doesn't exist
        if not repo_exists(repo_path):
            return "Repository doesn't exist locally"

        # Skip if settings file doesn't exist
        settings_path = os.path.join(repo_path, '.claude', 'settings.local.json')
        if not os.path.exists(settings_path):
            return "No Claude settings file found"

        return None
