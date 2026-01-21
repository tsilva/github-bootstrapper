"""Progress tracking utilities."""

import sys
import logging
from typing import List, Optional
from ..operations.base import OperationResult, OperationStatus

logger = logging.getLogger('github_bootstrapper')


class ProgressTracker:
    """Track and display progress for repository operations."""

    def __init__(self, total: int, operation_name: str):
        """Initialize progress tracker.

        Args:
            total: Total number of repositories to process
            operation_name: Name of the operation being performed
        """
        self.total = total
        self.operation_name = operation_name
        self.completed = 0
        self.success_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.current_repo: Optional[str] = None

    def update(self, result: OperationResult, current_repo: Optional[str] = None) -> None:
        """Update progress with a new result.

        Args:
            result: Operation result
            current_repo: Optional name of the current repo being processed
        """
        self.current_repo = current_repo
        self.completed += 1

        if result.status == OperationStatus.SUCCESS:
            self.success_count += 1
        elif result.status == OperationStatus.SKIPPED:
            self.skipped_count += 1
        else:
            self.failed_count += 1

        self.display()

    def display(self) -> None:
        """Display current progress."""
        # Calculate percentage
        percentage = (self.completed / self.total * 100) if self.total > 0 else 0

        # Create progress bar
        bar_width = 20
        filled = int(bar_width * self.completed / self.total) if self.total > 0 else 0
        bar = '█' * filled + '░' * (bar_width - filled)

        # Build status with current repo if available
        status = (
            f"\r[{bar}] {percentage:.0f}% ({self.completed}/{self.total}) "
        )

        if self.current_repo:
            status += f"Current: {self.current_repo} "

        status += f"✓{self.success_count} ⊘{self.skipped_count} ✗{self.failed_count}"

        # Write to stderr to avoid mixing with log output
        sys.stderr.write(status)
        sys.stderr.flush()

    def finish(self) -> None:
        """Finish progress tracking."""
        # Print newline to move past progress bar
        sys.stderr.write("\n")
        sys.stderr.flush()

        logger.info(f"Completed {self.operation_name} operation")
        logger.info(f"Total: {self.total}, Success: {self.success_count}, "
                   f"Skipped: {self.skipped_count}, Failed: {self.failed_count}")


def print_summary(results: List[OperationResult], operation_name: str) -> None:
    """Print operation summary.

    Args:
        results: List of operation results
        operation_name: Name of the operation
    """
    total = len(results)
    success = sum(1 for r in results if r.status == OperationStatus.SUCCESS)
    skipped = sum(1 for r in results if r.status == OperationStatus.SKIPPED)
    failed = sum(1 for r in results if r.status == OperationStatus.FAILED)

    print("\n" + "=" * 60)
    print(f"SUMMARY: {operation_name.upper()}")
    print("=" * 60)
    print(f"Total repositories: {total}")
    print(f"✓ Success: {success}")
    print(f"⊘ Skipped: {skipped}")
    print(f"✗ Failed: {failed}")

    # Print failed repositories
    if failed > 0:
        print("\nFailed repositories:")
        for result in results:
            if result.status == OperationStatus.FAILED:
                print(f"  - {result.repo_full_name}: {result.message}")

    # Print skipped repositories (if not too many)
    if skipped > 0 and skipped <= 10:
        print("\nSkipped repositories:")
        for result in results:
            if result.status == OperationStatus.SKIPPED:
                print(f"  - {result.repo_full_name}: {result.message}")

    print("=" * 60)
