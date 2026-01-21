"""Base class for Claude prompt templates."""

import os
from abc import ABC, abstractmethod
from typing import Dict, Tuple


def repo_exists(repo_path: str) -> bool:
    """Check if a repository exists locally."""
    return os.path.isdir(repo_path) and os.path.isdir(os.path.join(repo_path, '.git'))


class PromptTemplate(ABC):
    """Base class for Claude prompt templates.

    Subclasses should override:
    - name: Unique template identifier
    - description: Human-readable description
    - prompt: The Claude prompt text (supports {{variable}} substitution)
    - should_run(): Logic to determine if template should execute on a repo
    - get_variables(): Optional additional variables for substitution
    """

    # Class attributes to be overridden
    name: str = "base"
    description: str = "Base template"
    prompt: str = ""

    @abstractmethod
    def should_run(self, repo: Dict, repo_path: str) -> Tuple[bool, str]:
        """Determine if template should run on this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local filesystem path to repository

        Returns:
            (should_run, reason) - bool indicating if should run and explanation string
        """
        pass

    def get_variables(self, repo: Dict, repo_path: str) -> Dict[str, str]:
        """Get variables for substitution in prompt.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local filesystem path to repository

        Returns:
            Dictionary of variable name -> value for {{variable}} substitution
        """
        # Default variables available to all templates
        return {
            'repo_name': repo['name'],
            'repo_full_name': repo['full_name'],
            'default_branch': repo.get('default_branch', 'main'),
            'description': repo.get('description', ''),
            'language': repo.get('language', ''),
        }
