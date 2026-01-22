"""Raw prompt template for ad-hoc prompt execution."""

from typing import Dict, Tuple
from .base import PromptTemplate, repo_exists


class RawPromptTemplate(PromptTemplate):
    """Template for ad-hoc raw prompts.

    This template is not registered in the auto-discovery system.
    It's instantiated directly when a non-template prompt is provided.
    """

    name = "_raw"
    description = "Ad-hoc prompt execution"

    def __init__(self, prompt_text: str):
        """Initialize with custom prompt text.

        Args:
            prompt_text: The raw prompt to execute
        """
        self.prompt = prompt_text

    def should_run(self, repo: Dict, repo_path: str) -> Tuple[bool, str]:
        """Always run unless repo doesn't exist locally.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local filesystem path to repository

        Returns:
            (should_run, reason) tuple
        """
        if not repo_exists(repo_path):
            return False, "Repository doesn't exist locally"
        return True, "Will execute custom prompt"
