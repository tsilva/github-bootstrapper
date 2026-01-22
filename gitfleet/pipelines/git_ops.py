"""Git operation pipelines (sync, clone-only, pull-only)."""

from typing import Optional, Callable, Dict, Any

from .base import Pipeline
from ..predicates import (
    RepoExists,
    RepoClean,
    not_,
    all_of,
)
from ..actions.git import CloneAction, PullAction


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
