"""README template for README.md generation."""

import os
from typing import Dict, Tuple
from .base import PromptTemplate, repo_exists


class ReadmeTemplate(PromptTemplate):
    """Generate/update README.md for a repository."""

    name = "readme"
    description = "Generate or update README.md using readme-generator skill"
    prompt = (
        "Use the readme-generator skill to create a comprehensive README.md "
        "for this project. Analyze the codebase and generate appropriate "
        "documentation including installation, usage, features, and any other "
        "relevant sections."
    )

    def should_run(self, repo: Dict, repo_path: str) -> Tuple[bool, str]:
        """Skip archived repos, forks, and repos with existing README.md.

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

        readme_path = os.path.join(repo_path, 'README.md')
        if os.path.exists(readme_path):
            return False, "README.md already exists"

        return True, "README.md not found - will generate"
