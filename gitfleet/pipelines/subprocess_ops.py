"""Subprocess-based pipelines (description-sync, claude-exec)."""

from typing import Optional

from .base import Pipeline
from ..predicates import RepoExists, NotArchived, FileExists, all_of
from ..actions.description_sync import DescriptionSyncAction
from ..actions.claude_sdk import ClaudeSDKAction
from ..actions.subprocess_ops import ClaudeCliAction  # Kept as fallback


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


class ClaudePipeline(Pipeline):
    """Execute Claude prompt via SDK.

    This pipeline runs any prompt through the Claude Agent SDK, including skill
    invocations like "/readme-generator" or "/claude-settings-optimizer --mode analyze".

    Uses the claude-agent-sdk for:
    - Native Python objects instead of JSON parsing
    - Better error types with detailed info
    - Cost tracking (total_cost_usd)
    - Streaming support for long operations
    """

    name = "claude-exec"
    description = "Execute Claude prompt via SDK (supports skills via /skill-name)"
    requires_token = False
    safe_parallel = False  # Sequential for API rate limits
    show_progress_only = True

    def __init__(self, prompt: str, timeout: int = 300):
        """Initialize claude pipeline.

        Args:
            prompt: The prompt to execute (can be a skill like "/readme-generator")
            timeout: Timeout in seconds
        """
        super().__init__()

        # Only run if repo exists
        self.when(RepoExists())

        # Execute Claude via SDK (replaces ClaudeCliAction)
        self.then(ClaudeSDKAction(prompt=prompt, timeout=timeout))


# Factory functions
def create_description_sync_pipeline() -> DescriptionSyncPipeline:
    """Create a description-sync pipeline."""
    return DescriptionSyncPipeline()


def create_claude_pipeline(prompt: str, timeout: int = 300) -> ClaudePipeline:
    """Create a claude pipeline.

    Args:
        prompt: The prompt to execute
        timeout: Timeout in seconds

    Returns:
        Configured pipeline
    """
    return ClaudePipeline(prompt=prompt, timeout=timeout)
