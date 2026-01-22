"""Git-related actions (clone, pull, add, commit, push)."""

import logging
import subprocess
from typing import TYPE_CHECKING

from .base import Action
from ..core.types import ActionResult, Status

if TYPE_CHECKING:
    from ..core.types import RepoContext

logger = logging.getLogger('gitfleet')


class CloneAction(Action):
    """Clone a repository."""

    name = "clone"
    modifies_repo = True
    description = "Clone repository from remote"

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Clone the repository."""
        from ..utils.git import clone_repo

        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True}
            )

        # Get clone URL and execute
        clone_url = ctx.get_clone_url()
        logger.info(f"Cloning {ctx.repo_name}...")

        if clone_repo(clone_url, ctx.repo_path):
            return ActionResult(
                status=Status.SUCCESS,
                message="Cloned successfully",
                action_name=self.name,
                metadata={'clone_url': clone_url}
            )
        else:
            return ActionResult(
                status=Status.FAILED,
                message="Failed to clone",
                action_name=self.name,
                metadata={'clone_url': clone_url}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would clone {ctx.repo_name}"


class PullAction(Action):
    """Pull updates for a repository."""

    name = "pull"
    modifies_repo = True
    description = "Pull latest changes from remote"

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Pull updates for the repository."""
        from ..utils.git import pull_repo

        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True}
            )

        # Execute pull
        logger.info(f"Pulling updates for {ctx.repo_name}...")

        if pull_repo(ctx.repo_path):
            return ActionResult(
                status=Status.SUCCESS,
                message="Pulled latest changes",
                action_name=self.name
            )
        else:
            return ActionResult(
                status=Status.FAILED,
                message="Failed to pull changes",
                action_name=self.name
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would pull {ctx.repo_name}"


class FetchAction(Action):
    """Fetch from remote without merging."""

    name = "fetch"
    modifies_repo = False  # Fetch doesn't modify working directory
    description = "Fetch from remote"

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Fetch from remote."""
        import subprocess

        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True}
            )

        try:
            subprocess.run(
                ["git", "fetch"],
                cwd=ctx.repo_path,
                capture_output=True,
                check=True,
                timeout=30
            )
            return ActionResult(
                status=Status.SUCCESS,
                message="Fetched from remote",
                action_name=self.name
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return ActionResult(
                status=Status.FAILED,
                message=f"Failed to fetch: {e}",
                action_name=self.name
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would fetch {ctx.repo_name}"


class GitAddAction(Action):
    """Stage files for commit."""

    name = "git-add"
    modifies_repo = True
    description = "Stage files for commit"

    def __init__(self, files: str = "."):
        """Initialize git add action.

        Args:
            files: Files to stage (default: "." for all)
        """
        self.files = files

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Stage files for commit."""
        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True, 'files': self.files}
            )

        try:
            subprocess.run(
                ["git", "add", self.files],
                cwd=ctx.repo_path,
                capture_output=True,
                check=True,
                timeout=30
            )
            return ActionResult(
                status=Status.SUCCESS,
                message=f"Staged files: {self.files}",
                action_name=self.name,
                metadata={'files': self.files}
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return ActionResult(
                status=Status.FAILED,
                message=f"Failed to stage files: {e}",
                action_name=self.name,
                metadata={'files': self.files}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would stage files: {self.files}"


class GitCommitAction(Action):
    """Commit staged changes with a message from context."""

    name = "git-commit"
    modifies_repo = True
    description = "Commit staged changes"

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Commit staged changes."""
        message = ctx.get_variable('commit_message', 'Update')

        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True, 'message': message}
            )

        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=ctx.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return ActionResult(
                    status=Status.SUCCESS,
                    message="Committed changes",
                    action_name=self.name,
                    metadata={'message': message, 'output': result.stdout}
                )
            else:
                return ActionResult(
                    status=Status.FAILED,
                    message=f"Commit failed: {result.stderr}",
                    action_name=self.name,
                    metadata={'message': message, 'stderr': result.stderr}
                )
        except subprocess.TimeoutExpired:
            return ActionResult(
                status=Status.FAILED,
                message="Commit timed out",
                action_name=self.name,
                metadata={'message': message}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        message = ctx.get_variable('commit_message', 'Update')
        preview = message[:50] + "..." if len(message) > 50 else message
        return f"Would commit with message: {preview}"


class GitPushAction(Action):
    """Push commits to remote."""

    name = "git-push"
    modifies_repo = True
    description = "Push commits to remote"

    def __init__(self, timeout: int = 120):
        """Initialize git push action.

        Args:
            timeout: Timeout in seconds (default: 120)
        """
        self.timeout = timeout

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Push commits to remote."""
        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True}
            )

        try:
            result = subprocess.run(
                ["git", "push"],
                cwd=ctx.repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode == 0:
                return ActionResult(
                    status=Status.SUCCESS,
                    message="Pushed to remote",
                    action_name=self.name,
                    metadata={'output': result.stdout}
                )
            else:
                return ActionResult(
                    status=Status.FAILED,
                    message=f"Push failed: {result.stderr}",
                    action_name=self.name,
                    metadata={'stderr': result.stderr}
                )
        except subprocess.TimeoutExpired:
            return ActionResult(
                status=Status.FAILED,
                message=f"Push timed out after {self.timeout}s",
                action_name=self.name
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would push {ctx.repo_name} to remote"
