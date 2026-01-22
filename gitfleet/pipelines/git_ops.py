"""Git operation pipelines (sync, clone-only, pull-only, commit-push)."""

from typing import Optional, Callable, Dict, Any

from .base import Pipeline
from ..predicates import (
    RepoExists,
    RepoClean,
    HasUncommittedChanges,
    not_,
    all_of,
)
from ..actions.git import CloneAction, PullAction, GitAddAction, GitCommitAction, GitPushAction
from ..actions.subprocess_ops import ClaudeCommitMessageAction


class SyncPipeline(Pipeline):
    """Sync pipeline: clone new repos or pull existing ones.

    This replaces SyncOperation with a pipeline-based implementation.
    """

    name = "sync"
    description = "Clone new repos and pull updates for existing repos"
    requires_token = False
    safe_parallel = True

    def __init__(self):
        """Initialize sync pipeline."""
        super().__init__()

        # Branch 1: If repo doesn't exist, clone it
        self.branch(
            when=not_(RepoExists()),
            then=CloneAction()
        )

        # Branch 2: If repo exists and is clean, pull
        self.branch(
            when=all_of(RepoExists(), RepoClean()),
            then=PullAction()
        )

        # Note: If repo exists but is dirty, neither branch matches,
        # resulting in a no-op (which is correct behavior)


class CloneOnlyPipeline(Pipeline):
    """Clone-only pipeline: clone repositories that don't exist locally.

    This replaces CloneOnlyOperation with a pipeline-based implementation.
    """

    name = "clone-only"
    description = "Clone repositories that don't exist locally"
    requires_token = False
    safe_parallel = True

    def __init__(self):
        """Initialize clone-only pipeline."""
        super().__init__()

        # Only run if repo doesn't exist
        self.when(not_(RepoExists()))
        self.then(CloneAction())


class PullOnlyPipeline(Pipeline):
    """Pull-only pipeline: pull updates for existing repos.

    This replaces PullOnlyOperation with a pipeline-based implementation.
    """

    name = "pull-only"
    description = "Pull updates for repositories that exist locally"
    requires_token = False
    safe_parallel = True

    def __init__(self):
        """Initialize pull-only pipeline."""
        super().__init__()

        # Only run if repo exists and is clean
        self.when(RepoExists(), RepoClean())
        self.then(PullAction())


# Factory functions for creating pipelines with options
def create_sync_pipeline() -> SyncPipeline:
    """Create a sync pipeline."""
    return SyncPipeline()


def create_clone_only_pipeline() -> CloneOnlyPipeline:
    """Create a clone-only pipeline."""
    return CloneOnlyPipeline()


def create_pull_only_pipeline() -> PullOnlyPipeline:
    """Create a pull-only pipeline."""
    return PullOnlyPipeline()


class CommitPushPipeline(Pipeline):
    """Commit changes with Claude-generated message and push.

    This pipeline:
    1. Finds repos with uncommitted changes
    2. Stages all changes (git add .)
    3. Uses Claude to generate a commit message based on diff stats
    4. Shows message for user review/edit before committing
    5. Commits with the (possibly edited) message
    6. Pushes to remote
    """

    name = "commit-push"
    description = "Stage, commit (Claude-generated message), and push changes"
    requires_token = False
    safe_parallel = False  # Claude API rate limits + user interaction

    def __init__(self):
        """Initialize commit-push pipeline."""
        super().__init__()

        # Only run on repos with uncommitted changes
        self.when(RepoExists(), HasUncommittedChanges())

        # Sequential actions
        self.then(GitAddAction())
        self.then(ClaudeCommitMessageAction())
        self.then(GitCommitAction())
        self.then(GitPushAction())


def create_commit_push_pipeline() -> CommitPushPipeline:
    """Create a commit-push pipeline."""
    return CommitPushPipeline()
