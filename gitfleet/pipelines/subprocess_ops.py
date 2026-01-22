"""Subprocess-based pipelines (description-sync, claude-exec)."""

from typing import Optional

from .base import Pipeline
from ..predicates import RepoExists, NotArchived, FileExists, all_of
from ..actions.description_sync import DescriptionSyncAction
from ..actions.subprocess_ops import ClaudeCliAction


class DescriptionSyncPipeline(Pipeline):
    """Sync GitHub repo description with README tagline.

    This replaces DescriptionSyncOperation with a pipeline-based implementation.
    """

    name = "description-sync"
    description = "Sync GitHub repo description with README tagline"
    requires_token = False  # gh CLI handles auth
    safe_parallel = True

    def __init__(self):
        """Initialize description-sync pipeline."""
        super().__init__()

        # Only run for non-archived repos with README
        self.when(
            NotArchived(),
            RepoExists(),
            FileExists("README.md")
        )

        self.then(DescriptionSyncAction())


class ClaudeExecPipeline(Pipeline):
    """Execute Claude CLI with a prompt.

    Note: This is a simplified version. The full ClaudeExecOperation
    has additional features like templates, pre_batch_hooks, and
    variable substitution that would need to be handled separately.
    """

    name = "claude-exec"
    description = "Execute Claude CLI prompt"
    requires_token = False
    safe_parallel = False  # Sequential for API rate limits
    show_progress_only = True

    def __init__(self, prompt: str, timeout: int = 300):
        """Initialize claude-exec pipeline.

        Args:
            prompt: The prompt to execute
            timeout: Timeout in seconds
        """
        super().__init__()

        # Only run if repo exists
        self.when(RepoExists())

        # Execute Claude CLI
        self.then(ClaudeCliAction(prompt=prompt, timeout=timeout))


# Factory functions
def create_description_sync_pipeline() -> DescriptionSyncPipeline:
    """Create a description-sync pipeline."""
    return DescriptionSyncPipeline()


def create_claude_exec_pipeline(prompt: str, timeout: int = 300) -> ClaudeExecPipeline:
    """Create a claude-exec pipeline.

    Args:
        prompt: The prompt to execute
        timeout: Timeout in seconds

    Returns:
        Configured pipeline
    """
    return ClaudeExecPipeline(prompt=prompt, timeout=timeout)
