"""Init template for CLAUDE.md generation."""

import os
from typing import Dict, Tuple
from .base import PromptTemplate, repo_exists


class InitTemplate(PromptTemplate):
    """Initialize CLAUDE.md for a repository."""

    name = "init"
    description = "Initialize CLAUDE.md using Claude's /init command"
    prompt = "/init"

    def should_run(self, repo: Dict, repo_path: str) -> Tuple[bool, str]:
        """Skip archived repos, forks, and repos with existing CLAUDE.md.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local filesystem path to repository

        Returns:
            (should_run, reason) tuple
        """
        if not repo_exists(repo_path):
            return False, "Repository doesn't exist locally"

        if repo.get('archived', False):
            return False, "Repository is archived"

        if repo.get('fork', False):
            return False, "Repository is a fork"

        claude_md = os.path.join(repo_path, 'CLAUDE.md')
        if os.path.exists(claude_md):
            return False, "CLAUDE.md already exists"

        return True, "CLAUDE.md not found - will initialize"
