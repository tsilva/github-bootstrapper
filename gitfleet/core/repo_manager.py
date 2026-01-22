"""Repository manager for orchestrating operations."""

import logging
import multiprocessing
from typing import List, Dict, Any, Type, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .github_client import GitHubClient
from ..operations.base import Operation, OperationResult
from ..utils.progress import ProgressTracker

logger = logging.getLogger('gitfleet')


class RepoManager:
    """Manager for orchestrating repository operations."""

    def __init__(
        self,
        github_client: GitHubClient,
        base_dir: str,
        max_workers: int = None,
        sequential: bool = False
    ):
        """Initialize repository manager.

        Args:
            github_client: GitHub API client
            base_dir: Base directory for repositories
            max_workers: Maximum number of parallel workers (None = CPU count)
            sequential: Force sequential processing
        """
        self.github_client = github_client
        self.base_dir = base_dir
        self.sequential = sequential

        # Determine max workers
        if max_workers is None:
            self.max_workers = multiprocessing.cpu_count()
        else:
            self.max_workers = max_workers

    def execute_operation(
        self,
        operation_class: Type[Operation],
        repos: List[Dict[str, Any]],
        dry_run: bool = False,
        **operation_kwargs
    ) -> List[OperationResult]:
        """Execute an operation on a list of repositories.

        Args:
            operation_class: Operation class to instantiate
            repos: List of repository dictionaries
            dry_run: If True, preview without executing
            **operation_kwargs: Additional kwargs for operation constructor

        Returns:
            List of operation results
        """
        # Instantiate operation
        operation = operation_class(
            base_dir=self.base_dir,
            dry_run=dry_run,
            **operation_kwargs
        )

        logger.info(f"Executing operation: {operation.name}")
        logger.info(f"Description: {operation.description}")
        logger.info(f"Total repositories: {len(repos)}")
        logger.info(f"Dry run: {dry_run}")

        # Pre-filter repositories
        repos_to_execute = []
        repos_skipped = []

        for repo in repos:
            repo_path = operation.get_repo_path(repo)
            skip_reason = operation.should_skip(repo, repo_path)

            if skip_reason:
                repos_skipped.append((repo, skip_reason))
            else:
                repos_to_execute.append(repo)

        # Update repo count logging
        logger.info(f"Repositories to process: {len(repos_to_execute)}")
        if repos_skipped:
            logger.info(f"Repositories to skip: {len(repos_skipped)}")

        # Call pre-batch hook with filtered lists
        operation.pre_batch_hook(repos_to_execute, repos_skipped, self.base_dir, dry_run)

        # In dry-run mode, log all skip reasons
        if dry_run and repos_skipped:
            logger.info("\nSkipped repositories:")
            for repo, reason in repos_skipped:
                logger.info(f"  ⊘ {repo['full_name']}: {reason}")

        # Create progress tracker if needed
        progress_tracker = None
        if operation.show_progress_only:
            progress_tracker = ProgressTracker(len(repos_to_execute), operation.name)

        # Determine processing mode
        use_parallel = (
            not self.sequential and
            operation.safe_parallel
        )

        if use_parallel:
            logger.info(f"Using parallel processing with {self.max_workers} workers")
            results = self._execute_parallel(operation, repos_to_execute, progress_tracker)
        else:
            logger.info("Using sequential processing")
            results = self._execute_sequential(operation, repos_to_execute, progress_tracker)

        # Finish progress tracker
        if progress_tracker:
            progress_tracker.finish()

        # Call post-batch hook
        operation.post_batch_hook(results)

        return results

    def _execute_parallel(
        self,
        operation: Operation,
        repos: List[Dict[str, Any]],
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[OperationResult]:
        """Execute operation in parallel.

        Args:
            operation: Operation instance
            repos: List of repositories
            progress_tracker: Optional progress tracker for progress display

        Returns:
            List of operation results
        """
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_repo = {
                executor.submit(self._process_repo, operation, repo): repo
                for repo in repos
            }

            # Process completed tasks
            for future in as_completed(future_to_repo):
                result = future.result()
                results.append(result)

                # Update progress or log result
                if progress_tracker:
                    progress_tracker.update(result)
                else:
                    self._log_result(result)

        return results

    def _execute_sequential(
        self,
        operation: Operation,
        repos: List[Dict[str, Any]],
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[OperationResult]:
        """Execute operation sequentially.

        Args:
            operation: Operation instance
            repos: List of repositories
            progress_tracker: Optional progress tracker for progress display

        Returns:
            List of operation results
        """
        results = []
        for repo in repos:
            result = self._process_repo(operation, repo)
            results.append(result)

            # Update progress or log result
            if progress_tracker:
                # Pass repo name as current_repo when updating
                progress_tracker.update(result, current_repo=repo['full_name'])
            else:
                self._log_result(result)

        return results

    def _process_repo(
        self,
        operation: Operation,
        repo: Dict[str, Any]
    ) -> OperationResult:
        """Process a single repository.

        Args:
            operation: Operation instance
            repo: Repository dictionary

        Returns:
            Operation result
        """
        # Log repository info (unless using progress-only mode)
        if not operation.show_progress_only:
            logger.info(f"Repository: {repo['full_name']}")
            logger.info(f"  URL: {repo['html_url']}")
            logger.info(f"  Private: {repo['private']}")
            if repo.get('description'):
                logger.info(f"  Description: {repo['description']}")
            logger.info("---")

        # Get repo path
        repo_path = operation.get_repo_path(repo)

        # Execute operation
        try:
            result = operation.execute(repo, repo_path)
            return result
        except Exception as e:
            logger.error(f"Unexpected error processing {repo['name']}: {e}")
            from ..operations.base import OperationStatus
            return OperationResult(
                status=OperationStatus.FAILED,
                message=f"Unexpected error: {str(e)}",
                repo_name=repo['name'],
                repo_full_name=repo['full_name']
            )

    def _log_result(self, result: OperationResult) -> None:
        """Log an operation result.

        Args:
            result: Operation result
        """
        if result.success:
            logger.info(f"✓ {result.repo_name}: {result.message}")
        elif result.skipped:
            logger.info(f"⊘ {result.repo_name}: {result.message}")
        else:
            logger.error(f"✗ {result.repo_name}: {result.message}")
