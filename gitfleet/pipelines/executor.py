"""Pipeline executor for orchestrating pipeline execution."""

import os
import logging
import multiprocessing
from typing import List, Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import Pipeline
from ..core.types import RepoContext, ActionResult, Status
from ..operations.base import OperationResult, OperationStatus
from ..utils.progress import ProgressTracker

logger = logging.getLogger('gitfleet')


def action_result_to_operation_result(
    result: ActionResult,
    repo_name: str,
    repo_full_name: str
) -> OperationResult:
    """Convert ActionResult to OperationResult for backward compatibility.

    Args:
        result: ActionResult from pipeline
        repo_name: Repository name
        repo_full_name: Full repository name

    Returns:
        OperationResult for backward compatibility
    """
    # Map Status to OperationStatus
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


class PipelineExecutor:
    """Executor for running pipelines on repositories.

    This class adapts the RepoManager patterns to work with the new
    Pipeline architecture while maintaining backward compatibility.
    """

    def __init__(
        self,
        base_dir: str,
        max_workers: Optional[int] = None,
        sequential: bool = False,
        clone_url_getter: Optional[Callable[[Dict[str, Any]], str]] = None
    ):
        """Initialize pipeline executor.

        Args:
            base_dir: Base directory for repositories
            max_workers: Maximum parallel workers (None = CPU count)
            sequential: Force sequential processing
            clone_url_getter: Optional callable to get clone URL from repo dict
        """
        self.base_dir = base_dir
        self.sequential = sequential
        self.clone_url_getter = clone_url_getter

        if max_workers is None:
            self.max_workers = multiprocessing.cpu_count()
        else:
            self.max_workers = max_workers

    def execute(
        self,
        pipeline: Pipeline,
        repos: List[Dict[str, Any]],
        dry_run: bool = False,
        force: bool = False,
        yes: bool = False,
        **kwargs
    ) -> List[OperationResult]:
        """Execute a pipeline on a list of repositories.

        Args:
            pipeline: Pipeline to execute
            repos: List of repository dictionaries
            dry_run: If True, preview without executing
            force: If True, ignore pipeline predicates
            yes: If True, skip confirmation prompt
            **kwargs: Additional kwargs for context variables

        Returns:
            List of OperationResults for backward compatibility
        """
        # Pre-filter repositories using pipeline predicates
        repos_to_execute = []
        repos_skipped: List[Tuple[Dict[str, Any], str]] = []

        for repo in repos:
            repo_path = os.path.join(self.base_dir, repo['name'])
            ctx = self._create_context(repo, repo_path, dry_run, force, **kwargs)

            if not force:
                skip_reason = pipeline.should_skip(ctx)
                if skip_reason:
                    repos_skipped.append((repo, skip_reason))
                    continue

            repos_to_execute.append(repo)

        # Show execution preview
        print(f"\n{'='*60}")
        print(f"Pipeline: {pipeline.name}")
        print(f"Description: {pipeline.description}")
        print(f"{'='*60}")
        print(f"\nRepositories to process ({len(repos_to_execute)}):")
        for repo in repos_to_execute:
            print(f"  • {repo['full_name']}")

        if repos_skipped:
            print(f"\nRepositories to skip ({len(repos_skipped)}):")
            for repo, reason in repos_skipped:
                print(f"  ⊘ {repo['full_name']}: {reason}")

        print(f"\nDry run: {dry_run}")
        print(f"{'='*60}\n")

        # No repos to process
        if not repos_to_execute:
            print("No repositories to process.")
            return []

        # Prompt for confirmation (unless --yes flag)
        if not yes and not dry_run:
            if not self._confirm_execution():
                print("Operation cancelled.")
                return []

        logger.info(f"Executing pipeline: {pipeline.name}")
        logger.info(f"Repositories to process: {len(repos_to_execute)}")

        # Create progress tracker if needed
        progress_tracker = None
        if pipeline.show_progress_only:
            progress_tracker = ProgressTracker(len(repos_to_execute), pipeline.name)

        # Determine processing mode
        use_parallel = (
            not self.sequential and
            pipeline.safe_parallel
        )

        if use_parallel:
            logger.info(f"Using parallel processing with {self.max_workers} workers")
            results = self._execute_parallel(
                pipeline, repos_to_execute, dry_run, force, progress_tracker, **kwargs
            )
        else:
            logger.info("Using sequential processing")
            results = self._execute_sequential(
                pipeline, repos_to_execute, dry_run, force, progress_tracker, **kwargs
            )

        # Finish progress tracker
        if progress_tracker:
            progress_tracker.finish()

        return results

    def _create_context(
        self,
        repo: Dict[str, Any],
        repo_path: str,
        dry_run: bool,
        force: bool,
        **kwargs
    ) -> RepoContext:
        """Create a RepoContext for a repository.

        Args:
            repo: Repository dictionary
            repo_path: Local path
            dry_run: Dry run mode
            force: Force mode
            **kwargs: Additional variables

        Returns:
            RepoContext instance
        """
        return RepoContext(
            repo=repo,
            repo_path=repo_path,
            base_dir=self.base_dir,
            dry_run=dry_run,
            force=force,
            variables=kwargs,
            clone_url_getter=self.clone_url_getter
        )

    def _execute_parallel(
        self,
        pipeline: Pipeline,
        repos: List[Dict[str, Any]],
        dry_run: bool,
        force: bool,
        progress_tracker: Optional[ProgressTracker],
        **kwargs
    ) -> List[OperationResult]:
        """Execute pipeline in parallel."""
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_repo = {
                executor.submit(
                    self._process_repo, pipeline, repo, dry_run, force, **kwargs
                ): repo
                for repo in repos
            }

            for future in as_completed(future_to_repo):
                result = future.result()
                results.append(result)

                if progress_tracker:
                    progress_tracker.update(result)
                else:
                    self._log_result(result)

        return results

    def _execute_sequential(
        self,
        pipeline: Pipeline,
        repos: List[Dict[str, Any]],
        dry_run: bool,
        force: bool,
        progress_tracker: Optional[ProgressTracker],
        **kwargs
    ) -> List[OperationResult]:
        """Execute pipeline sequentially."""
        results = []

        for repo in repos:
            result = self._process_repo(pipeline, repo, dry_run, force, **kwargs)
            results.append(result)

            if progress_tracker:
                progress_tracker.update(result, current_repo=repo['full_name'])
            else:
                self._log_result(result)

        return results

    def _process_repo(
        self,
        pipeline: Pipeline,
        repo: Dict[str, Any],
        dry_run: bool,
        force: bool,
        **kwargs
    ) -> OperationResult:
        """Process a single repository with the pipeline.

        Args:
            pipeline: Pipeline to execute
            repo: Repository dictionary
            dry_run: Dry run mode
            force: Force mode
            **kwargs: Additional context variables

        Returns:
            OperationResult for backward compatibility
        """
        repo_name = repo['name']
        repo_full_name = repo['full_name']
        repo_path = os.path.join(self.base_dir, repo_name)

        # Log repository info (unless using progress-only mode)
        if not pipeline.show_progress_only:
            logger.info(f"Repository: {repo_full_name}")
            logger.info(f"  URL: {repo['html_url']}")
            logger.info(f"  Private: {repo['private']}")
            if repo.get('description'):
                logger.info(f"  Description: {repo['description']}")
            logger.info("---")

        # Create context and execute
        ctx = self._create_context(repo, repo_path, dry_run, force, **kwargs)

        try:
            action_result = pipeline.execute(ctx)
            return action_result_to_operation_result(
                action_result, repo_name, repo_full_name
            )
        except Exception as e:
            logger.error(f"Unexpected error processing {repo_name}: {e}")
            return OperationResult(
                status=OperationStatus.FAILED,
                message=f"Unexpected error: {str(e)}",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

    def _log_result(self, result: OperationResult) -> None:
        """Log an operation result."""
        if result.success:
            logger.info(f"✓ {result.repo_name}: {result.message}")
        elif result.skipped:
            logger.info(f"⊘ {result.repo_name}: {result.message}")
        else:
            logger.error(f"✗ {result.repo_name}: {result.message}")

    def _confirm_execution(self) -> bool:
        """Prompt user for confirmation before execution.

        Returns:
            True if user confirms, False otherwise
        """
        try:
            tty = open('/dev/tty', 'r')
        except OSError:
            # No TTY available, proceed without confirmation
            logger.warning("No TTY available, proceeding without confirmation")
            return True

        try:
            print("Proceed? [y/N]: ", end="", flush=True)
            response = tty.readline().strip().lower()
            return response in ('y', 'yes')
        finally:
            tty.close()
