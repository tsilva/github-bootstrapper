"""Configuration management for GitHub Bootstrapper."""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration for GitHub Bootstrapper.

    Merges environment variables with CLI arguments.
    CLI arguments take precedence over environment variables.
    """

    github_username: str
    repos_base_dir: str
    github_token: Optional[str] = None
    max_workers: Optional[int] = None
    sequential: bool = False

    @classmethod
    def from_env_and_args(
        cls,
        username: Optional[str] = None,
        repos_dir: Optional[str] = None,
        token: Optional[str] = None,
        max_workers: Optional[int] = None,
        sequential: bool = False
    ) -> 'Config':
        """Create config from environment variables and CLI arguments.

        CLI arguments override environment variables.

        Args:
            username: GitHub username (overrides GITHUB_USERNAME)
            repos_dir: Base directory for repos (overrides REPOS_BASE_DIR)
            token: GitHub token (overrides GITHUB_TOKEN)
            max_workers: Maximum parallel workers
            sequential: Force sequential processing

        Returns:
            Config instance

        Raises:
            ValueError: If required config is missing
        """
        # Merge with environment variables (CLI args take precedence)
        final_username = username or os.getenv('GITHUB_USERNAME')
        final_repos_dir = repos_dir or os.getenv('REPOS_BASE_DIR')
        final_token = token or os.getenv('GITHUB_TOKEN')

        # Validate required fields
        if not final_username:
            raise ValueError(
                "GitHub username is required. "
                "Set GITHUB_USERNAME in .env or use --username"
            )

        if not final_repos_dir:
            raise ValueError(
                "Repository base directory is required. "
                "Set REPOS_BASE_DIR in .env or use --repos-dir"
            )

        if not os.path.isdir(final_repos_dir):
            raise ValueError(
                f"REPOS_BASE_DIR '{final_repos_dir}' does not exist or is not a directory"
            )

        return cls(
            github_username=final_username,
            repos_base_dir=final_repos_dir,
            github_token=final_token,
            max_workers=max_workers,
            sequential=sequential
        )

    @property
    def is_authenticated(self) -> bool:
        """Check if GitHub token is available.

        Returns:
            True if token is available
        """
        return bool(self.github_token)
