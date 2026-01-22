"""Adapter to make pipelines work as operations for backward compatibility."""

import os
from typing import Dict, Any, Optional, List, Tuple, Callable

from .base import Pipeline
from ..core.types import RepoContext, Status
from ..operations.base import Operation, OperationResult, OperationStatus


class PipelineAsOperation(Operation):
    """Adapter that wraps a Pipeline to work as an Operation.

    This allows pipelines to be used with the existing RepoManager
    infrastructure while providing backward compatibility.

    Example usage:
        from gitfleet.pipelines import SyncPipeline
        from gitfleet.pipelines.adapter import PipelineAsOperation

        # Create an operation from a pipeline
        sync_op = PipelineAsOperation(SyncPipeline())

        # Use with RepoManager
        repo_manager.execute_operation(type(sync_op), repos)
    """

    def __init__(
        self,
        pipeline: Pipeline,
        base_dir: str = "",
        dry_run: bool = False,
        force: bool = False,
        clone_url_getter: Optional[Callable[[Dict[str, Any]], str]] = None,
        **kwargs
    ):
        """Initialize the adapter.

        Args:
            pipeline: The pipeline to wrap
            base_dir: Base directory for repositories
            dry_run: If True, don't actually execute operations
            force: If True, ignore pipeline predicates
            clone_url_getter: Optional callable to get clone URL
            **kwargs: Additional parameters passed to context
        """
        super().__init__(base_dir, dry_run, **kwargs)
        self._pipeline = pipeline
        self._force = force
        self._clone_url_getter = clone_url_getter
        self._extra_kwargs = kwargs

        # Copy pipeline attributes to operation
        self.name = pipeline.name
        self.description = pipeline.description
        self.requires_token = pipeline.requires_token
        self.safe_parallel = pipeline.safe_parallel
        self.show_progress_only = pipeline.show_progress_only
        self.default_workers = pipeline.default_workers

    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute the wrapped pipeline as an operation.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            OperationResult indicating success/failure/skip
        """
        repo_name = repo['name']
        repo_full_name = repo['full_name']

        # Create context
        ctx = RepoContext(
            repo=repo,
            repo_path=repo_path,
            base_dir=self.base_dir,
            dry_run=self.dry_run,
            force=self._force,
            variables=self._extra_kwargs.copy(),
            clone_url_getter=self._clone_url_getter
        )

        # Execute pipeline
        result = self._pipeline.execute(ctx)

        # Convert to OperationResult
        status_map = {
            Status.SUCCESS: OperationStatus.SUCCESS,
            Status.SKIPPED: OperationStatus.SKIPPED,
            Status.FAILED: OperationStatus.FAILED,
        }

        return OperationResult(
            status=status_map[result.status],
            message=result.message,
            repo_name=repo_name,
            repo_full_name=repo_full_name
        )

    def should_skip(self, repo: Dict[str, Any], repo_path: str) -> Optional[str]:
        """Check if pipeline should skip this repository.

        Args:
            repo: Repository dictionary
            repo_path: Local path

        Returns:
            Skip reason if should skip, None otherwise
        """
        if self._force:
            return None

        ctx = RepoContext(
            repo=repo,
            repo_path=repo_path,
            base_dir=self.base_dir,
            dry_run=self.dry_run,
            force=self._force,
            clone_url_getter=self._clone_url_getter
        )

        return self._pipeline.should_skip(ctx)


def pipeline_to_operation_class(pipeline_class: type) -> type:
    """Create an Operation class from a Pipeline class.

    This creates a new class that can be used with OperationRegistry
    and RepoManager.

    Args:
        pipeline_class: Pipeline class to convert

    Returns:
        Operation class that wraps the pipeline
    """
    # Create a sample pipeline to get attributes
    sample = pipeline_class()

    class PipelineWrappedOperation(Operation):
        """Operation wrapping a Pipeline."""

        name = sample.name
        description = sample.description
        requires_token = sample.requires_token
        safe_parallel = sample.safe_parallel
        show_progress_only = sample.show_progress_only
        default_workers = sample.default_workers

        def __init__(
            self,
            base_dir: str,
            dry_run: bool = False,
            force: bool = False,
            clone_url_getter: Optional[Callable[[Dict[str, Any]], str]] = None,
            **kwargs
        ):
            super().__init__(base_dir, dry_run, **kwargs)
            self._pipeline = pipeline_class()
            self._force = force
            self._clone_url_getter = clone_url_getter
            self._extra_kwargs = kwargs

        def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
            ctx = RepoContext(
                repo=repo,
                repo_path=repo_path,
                base_dir=self.base_dir,
                dry_run=self.dry_run,
                force=self._force,
                variables=self._extra_kwargs.copy(),
                clone_url_getter=self._clone_url_getter
            )

            result = self._pipeline.execute(ctx)

            status_map = {
                Status.SUCCESS: OperationStatus.SUCCESS,
                Status.SKIPPED: OperationStatus.SKIPPED,
                Status.FAILED: OperationStatus.FAILED,
            }

            return OperationResult(
                status=status_map[result.status],
                message=result.message,
                repo_name=repo['name'],
                repo_full_name=repo['full_name']
            )

        def should_skip(self, repo: Dict[str, Any], repo_path: str) -> Optional[str]:
            if self._force:
                return None

            ctx = RepoContext(
                repo=repo,
                repo_path=repo_path,
                base_dir=self.base_dir,
                dry_run=self.dry_run,
                force=self._force,
                clone_url_getter=self._clone_url_getter
            )

            return self._pipeline.should_skip(ctx)

    # Set class name for debugging
    PipelineWrappedOperation.__name__ = f"{pipeline_class.__name__}AsOperation"
    PipelineWrappedOperation.__qualname__ = PipelineWrappedOperation.__name__

    return PipelineWrappedOperation
