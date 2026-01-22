"""Status operation: report repository synchronization status."""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict
from .base import Operation, OperationResult, OperationStatus
from ..utils.git import repo_exists, get_sync_status

logger = logging.getLogger('gitfleet')


class StatusOperation(Operation):
    """Status operation: report repository synchronization status."""

    name = "status"
    description = "Report repository synchronization status"
    requires_token = False
    safe_parallel = True
    show_progress_only = True  # Show progress bar instead of individual logs
    default_workers = 8  # Status checks are I/O bound, benefit from more workers

    def __init__(self, base_dir: str, dry_run: bool = False, fetch: bool = True, clone_url_getter=None):
        """Initialize status operation.

        Args:
            base_dir: Base directory for repositories
            dry_run: If True, don't actually execute operations
            fetch: Whether to fetch from remote before checking status
            clone_url_getter: Ignored (for compatibility with operation framework)
        """
        super().__init__(base_dir, dry_run)
        self.fetch = fetch
        self.categories = defaultdict(list)

    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute status operation on a repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            OperationResult indicating repository status
        """
        repo_name = repo['name']
        repo_full_name = repo['full_name']

        # Check if repo exists locally
        if not repo_exists(repo_path):
            message = "Not cloned"
            self.categories[message].append(repo_full_name)
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message=message,
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Handle dry run
        if self.dry_run:
            message = "Dry run: Would check status"
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message=message,
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Get sync status
        status = get_sync_status(repo_path, fetch=self.fetch)

        # Handle detached HEAD
        if status['current_branch'] == "HEAD":
            message = "Detached HEAD"
            self.categories[message].append(repo_full_name)
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message=message,
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Handle no remote tracking
        if not status['has_remote']:
            message = "No remote tracking"
            self.categories[message].append(repo_full_name)
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message=message,
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Categorize based on status
        if status['has_changes']:
            message = "Uncommitted changes"
            self.categories[message].append(repo_full_name)
        elif status['behind'] > 0 and status['ahead'] > 0:
            message = f"Diverged (ahead {status['ahead']}, behind {status['behind']})"
            self.categories["Diverged"].append((repo_full_name, status['ahead'], status['behind']))
        elif status['behind'] > 0:
            message = f"Unpulled changes (behind {status['behind']})"
            self.categories["Unpulled changes"].append((repo_full_name, status['behind']))
        elif status['ahead'] > 0:
            message = f"Unpushed changes (ahead {status['ahead']})"
            self.categories["Unpushed changes"].append((repo_full_name, status['ahead']))
        else:
            message = "In sync"
            self.categories[message].append(repo_full_name)

        return OperationResult(
            status=OperationStatus.SUCCESS,
            message=message,
            repo_name=repo_name,
            repo_full_name=repo_full_name
        )

    def should_skip(self, repo: Dict[str, Any], repo_path: str) -> Optional[str]:
        """Check if status check should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            None (never skip - report status for all repos)
        """
        return None

    def post_batch_hook(self, results: List[OperationResult]) -> None:
        """Print status distribution summary after processing all repositories.

        Args:
            results: List of operation results
        """
        if not self.categories:
            return

        print("\n" + "=" * 60)
        print("STATUS DISTRIBUTION")
        print("=" * 60)

        # Define order for categories
        category_order = [
            "In sync",
            "Unpushed changes",
            "Unpulled changes",
            "Diverged",
            "Uncommitted changes",
            "Detached HEAD",
            "No remote tracking",
            "Not cloned"
        ]

        for category in category_order:
            if category not in self.categories:
                continue

            repos = self.categories[category]
            count = len(repos)
            print(f"\n{category}: {count} {'repository' if count == 1 else 'repositories'}")

            # Always show repo list for actionable categories, otherwise only if 10 or fewer
            always_list = {"Uncommitted changes", "Unpushed changes", "Unpulled changes", "Diverged", "Not cloned"}
            if category in always_list or count <= 10:
                for repo_info in repos:
                    if isinstance(repo_info, tuple):
                        # Repos with counts (diverged, unpulled, unpushed)
                        if category == "Diverged":
                            repo_name, ahead, behind = repo_info
                            print(f"  - {repo_name} (ahead {ahead}, behind {behind})")
                        else:
                            repo_name, count_val = repo_info
                            count_type = "ahead" if category == "Unpushed changes" else "behind"
                            print(f"  - {repo_name} ({count_type} {count_val})")
                    else:
                        # Simple repo names
                        print(f"  - {repo_info}")

        print("=" * 60)
