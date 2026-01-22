"""Core package for gitfleet."""

from .types import (
    Status,
    OperationStatus,
    ActionResult,
    OperationResult,
    RepoContext,
)

from .registry import Registry

from .github_client import GitHubClient
from .logger import setup_logging

__all__ = [
    # Types
    'Status',
    'OperationStatus',
    'ActionResult',
    'OperationResult',
    'RepoContext',
    # Registry
    'Registry',
    # Existing
    'GitHubClient',
    'setup_logging',
]
