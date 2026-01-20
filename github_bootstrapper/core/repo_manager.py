"""Repository manager for orchestrating operations."""

import logging
import multiprocessing
from typing import List, Dict, Any, Type
from concurrent.futures import ThreadPoolExecutor, as_completed

from .github_client import GitHubClient
from ..operations.base import Operation, OperationResult

logger = logging.getLogger('github_bootstrapper')


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
        logger.info(f"Repositories: {len(repos)}")
        logger.info(f"Dry run: {dry_run}")

        # Call pre-batch hook
        operation.pre_batch_hook(repos)

        # Determine processing mode
        use_parallel = (
            not self.sequential and
            operation.safe_parallel
        )

        if use_parallel:
            logger.info(f"Using parallel processing with {self.max_workers} workers")
            results = self._execute_parallel(operation, repos)
        else:
            logger.info("Using sequential processing")
            results = self._execute_sequential(operation, repos)

        # Call post-batch hook
        operation.post_batch_hook(results)

        return results

    def _execute_parallel(
        self,
        operation: Operation,
        repos: List[Dict[str, Any]]
    ) -> List[OperationResult]:
        """Execute operation in parallel.

        Args:
            operation: Operation instance
            repos: List of repositories

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

                # Log result
                self._log_result(result)

        return results

    def _execute_sequential(
        self,
        operation: Operation,
        repos: List[Dict[str, Any]]
    ) -> List[OperationResult]:
        """Execute operation sequentially.

        Args:
            operation: Operation instance
            repos: List of repositories

        Returns:
            List of operation results
        """
        results = []
        for repo in repos:
            result = self._process_repo(operation, repo)
            results.append(result)

            # Log result
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
        # Log repository info
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
