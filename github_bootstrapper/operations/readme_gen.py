"""README generation operation: generate/update README.md using Claude."""

import os
import subprocess
import logging
from typing import Dict, Any
from .base import Operation, OperationResult, OperationStatus
from ..utils.git import repo_exists

logger = logging.getLogger('github_bootstrapper')


class ReadmeGenOperation(Operation):
    """README generation operation: generate/update README.md using readme-generator skill."""

    name = "readme-gen"
    description = "Generate or update README.md using Claude's readme-generator skill"
    requires_token = False
    safe_parallel = False  # Claude API has rate limits

    def __init__(
        self,
        base_dir: str,
        dry_run: bool = False,
        force: bool = False
    ):
        """Initialize readme-gen operation.

        Args:
            base_dir: Base directory for repositories
            dry_run: If True, don't actually execute operations
            force: If True, regenerate even if README exists
        """
        super().__init__(base_dir, dry_run)
        self.force = force

    def should_skip(self, repo: Dict[str, Any], repo_path: str) -> str:
        """Check if readme-gen should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            Skip reason if should skip, None otherwise
        """
        # Skip if repo doesn't exist
        if not repo_exists(repo_path):
            return "Repository doesn't exist locally"

        # Skip archived repos by default
        if repo.get('archived', False):
            return "Repository is archived"

        # Skip forks by default
        if repo.get('fork', False):
            return "Repository is a fork"

        # Skip if README exists and not forcing
        readme_path = os.path.join(repo_path, 'README.md')
        if os.path.exists(readme_path) and not self.force:
            return "README.md already exists (use --force to regenerate)"

        return None

    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute readme-gen operation on a repository.

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
            action = "regenerate" if self.force else "generate"
            logger.info(f"[DRY RUN] Would {action} README for {repo_name}")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message=f"Dry run: Would {action} README",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Generate README using Claude CLI
        try:
            # Build prompt for Claude
            prompt = (
                "Use the readme-generator skill to create a comprehensive README.md "
                "for this project. Analyze the codebase and generate appropriate "
                "documentation including installation, usage, features, and any other "
                "relevant sections."
            )

            # Build command
            cmd = [
                'claude',
                '-p', prompt,
                '--permission-mode', 'acceptEdits',
                '--output-format', 'json'
            ]

            logger.info(f"Generating README for {repo_name} using Claude CLI...")
            logger.info(f"This may take a few minutes...")

            # Execute command with timeout (5 minutes)
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info(f"README generated successfully for {repo_name}")

                # Check if README was actually created/updated
                readme_path = os.path.join(repo_path, 'README.md')
                if os.path.exists(readme_path):
                    return OperationResult(
                        status=OperationStatus.SUCCESS,
                        message="README generated successfully",
                        repo_name=repo_name,
                        repo_full_name=repo_full_name
                    )
                else:
                    logger.warning(f"Claude completed but README.md not found for {repo_name}")
                    return OperationResult(
                        status=OperationStatus.FAILED,
                        message="Claude completed but README not created",
                        repo_name=repo_name,
                        repo_full_name=repo_full_name
                    )
            else:
                error = result.stderr or result.stdout
                logger.error(f"Failed to generate README for {repo_name}: {error[:200]}")
                return OperationResult(
                    status=OperationStatus.FAILED,
                    message=f"Claude CLI failed: {error[:100]}",
                    repo_name=repo_name,
                    repo_full_name=repo_full_name
                )

        except subprocess.TimeoutExpired:
            logger.error(f"README generation timed out for {repo_name}")
            return OperationResult(
                status=OperationStatus.FAILED,
                message="Operation timed out (5 minutes)",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )
        except FileNotFoundError:
            logger.error("Claude CLI not found. Please ensure Claude Code is installed.")
            return OperationResult(
                status=OperationStatus.FAILED,
                message="Claude CLI not found",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )
        except Exception as e:
            logger.error(f"Failed to generate README for {repo_name}: {e}")
            return OperationResult(
                status=OperationStatus.FAILED,
                message=f"Unexpected error: {str(e)}",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )
