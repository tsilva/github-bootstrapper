"""Base classes for repository operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum


class OperationStatus(Enum):
    """Status of an operation execution."""
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class OperationResult:
    """Result of a single operation execution."""
    status: OperationStatus
    message: str
    repo_name: str
    repo_full_name: str

    @property
    def success(self) -> bool:
        """Check if operation was successful."""
        return self.status == OperationStatus.SUCCESS

    @property
    def skipped(self) -> bool:
        """Check if operation was skipped."""
        return self.status == OperationStatus.SKIPPED

    @property
    def failed(self) -> bool:
        """Check if operation failed."""
        return self.status == OperationStatus.FAILED


class Operation(ABC):
    """Abstract base class for repository operations."""

    # Class attributes to be overridden by subclasses
    name: str = "base"
    description: str = "Base operation"
    requires_token: bool = False
    safe_parallel: bool = True
    show_progress_only: bool = False  # If True, show progress bar instead of individual logs

    def __init__(self, base_dir: str, dry_run: bool = False, **kwargs):
        """Initialize operation.

        Args:
            base_dir: Base directory for repositories
            dry_run: If True, don't actually execute operations
            **kwargs: Additional operation-specific parameters (ignored by base class)
        """
        self.base_dir = base_dir
        self.dry_run = dry_run

    @abstractmethod
    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute the operation on a repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            OperationResult indicating success/failure/skip
        """
        pass

    def should_skip(self, repo: Dict[str, Any], repo_path: str) -> Optional[str]:
        """Check if operation should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            Skip reason if should skip, None otherwise
        """
        return None

    def pre_batch_hook(self, repos: List[Dict[str, Any]]) -> None:
        """Hook called before processing batch of repositories.

        Args:
            repos: List of repositories to process
        """
        pass

    def post_batch_hook(self, results: List[OperationResult]) -> None:
        """Hook called after processing batch of repositories.

        Args:
            results: List of operation results
        """
        pass

    def get_repo_path(self, repo: Dict[str, Any]) -> str:
        """Get local path for a repository.

        Args:
            repo: Repository dictionary from GitHub API

        Returns:
            Local repository path
        """
        import os
        return os.path.join(self.base_dir, repo['name'])
