"""Core package for gitfleet."""

from .types import (
    Status,
    ActionResult,
    RepoContext,
)

from .registry import Registry

from .github_client import GitHubClient
from .repo_manager import RepoManager
from .logger import setup_logging

__all__ = [
    # Types
    'Status',
    'ActionResult',
    'RepoContext',
    # Registry
    'Registry',
    # Existing
    'GitHubClient',
    'RepoManager',
    'setup_logging',
]
