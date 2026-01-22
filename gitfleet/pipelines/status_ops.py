"""Status pipeline for repository synchronization status."""

import threading
from collections import defaultdict
from typing import List, Dict, Any

from .base import Pipeline
from ..actions.base import Action
from ..core.types import RepoContext, ActionResult, Status, OperationResult
from ..utils.git import repo_exists, get_sync_status


class StatusCheckAction(Action):
    """Action to check repository synchronization status."""

    name = "status-check"
    description = "Check repository synchronization status"

    def __init__(self, fetch: bool = True, categories: Dict[str, List] = None, lock: threading.Lock = None):
        """Initialize status check action.

        Args:
            fetch: Whether to fetch from remote before checking status
            categories: Shared dictionary for aggregating categories (thread-safe)
            lock: Lock for thread-safe access to categories
        """
        self.fetch = fetch
        self.categories = categories if categories is not None else defaultdict(list)
        self.lock = lock if lock is not None else threading.Lock()

    def execute(self, ctx: RepoContext) -> ActionResult:
        """Execute status check on a repository.

        Args:
            ctx: Repository context

        Returns:
            ActionResult indicating repository status
        """
        repo_path = ctx.repo_path
        repo_full_name = ctx.repo_full_name

        # Check if repo exists locally
        if not repo_exists(repo_path):
            message = "Not cloned"
            with self.lock:
                self.categories[message].append(repo_full_name)
            return ActionResult(
                status=Status.SUCCESS,
                message=message,
                action_name=self.name
            )

        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message="Dry run: Would check status",
                action_name=self.name
            )

        # Get sync status
        status = get_sync_status(repo_path, fetch=self.fetch)

        # Handle detached HEAD
        if status['current_branch'] == "HEAD":
            message = "Detached HEAD"
            with self.lock:
                self.categories[message].append(repo_full_name)
            return ActionResult(
                status=Status.SUCCESS,
                message=message,
                action_name=self.name
            )

        # Handle no remote tracking
        if not status['has_remote']:
            message = "No remote tracking"
            with self.lock:
                self.categories[message].append(repo_full_name)
            return ActionResult(
                status=Status.SUCCESS,
                message=message,
                action_name=self.name
            )

        # Categorize based on status
        if status['has_changes']:
            message = "Uncommitted changes"
            with self.lock:
                self.categories[message].append(repo_full_name)
        elif status['behind'] > 0 and status['ahead'] > 0:
            message = f"Diverged (ahead {status['ahead']}, behind {status['behind']})"
            with self.lock:
                self.categories["Diverged"].append((repo_full_name, status['ahead'], status['behind']))
        elif status['behind'] > 0:
            message = f"Unpulled changes (behind {status['behind']})"
            with self.lock:
                self.categories["Unpulled changes"].append((repo_full_name, status['behind']))
        elif status['ahead'] > 0:
            message = f"Unpushed changes (ahead {status['ahead']})"
            with self.lock:
                self.categories["Unpushed changes"].append((repo_full_name, status['ahead']))
        else:
            message = "In sync"
            with self.lock:
                self.categories[message].append(repo_full_name)

        return ActionResult(
            status=Status.SUCCESS,
            message=message,
            action_name=self.name
        )


class StatusPipeline(Pipeline):
    """Pipeline to report repository synchronization status.

    Checks local repository status against remote and categorizes repos into:
    - In sync
    - Unpushed changes
    - Unpulled changes
    - Diverged
    - Uncommitted changes
    - Detached HEAD
    - No remote tracking
    - Not cloned
    """

    name = "status"
    description = "Report repository synchronization status"
    requires_token = False
    safe_parallel = True
    show_progress_only = True
    default_workers = 8  # Status checks are I/O bound, benefit from more workers

    def __init__(self, fetch: bool = True):
        """Initialize status pipeline.

        Args:
            fetch: Whether to fetch from remote before checking status
        """
        super().__init__()
        self.fetch = fetch
        # Thread-safe category aggregation
        self.categories: Dict[str, List] = defaultdict(list)
        self.lock = threading.Lock()

        # Add the status check action with shared categories
        self.then(StatusCheckAction(
            fetch=fetch,
            categories=self.categories,
            lock=self.lock
        ))

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
