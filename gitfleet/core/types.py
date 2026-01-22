"""Core types for the pipeline architecture."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum


class Status(Enum):
    """Status of an action execution."""
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class ActionResult:
    """Result of a single action execution with rich metadata."""
    status: Status
    message: str
    action_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if action was successful."""
        return self.status == Status.SUCCESS

    @property
    def skipped(self) -> bool:
        """Check if action was skipped."""
        return self.status == Status.SKIPPED

    @property
    def failed(self) -> bool:
        """Check if action failed."""
        return self.status == Status.FAILED


@dataclass
class RepoContext:
    """Rich execution context for pipeline actions.

    This context is passed through the pipeline, accumulating results
    from each action and providing access to all necessary data.
    """
    repo: Dict[str, Any]  # GitHub API data
    repo_path: str        # Local path
    base_dir: str         # Base directory for all repos
    dry_run: bool = False
    force: bool = False
    variables: Dict[str, Any] = field(default_factory=dict)
    results: List[ActionResult] = field(default_factory=list)
    # Optional callable to get clone URL
    clone_url_getter: Optional[Callable[[Dict[str, Any]], str]] = None

    @property
    def repo_name(self) -> str:
        """Get repository name."""
        return self.repo['name']

    @property
    def repo_full_name(self) -> str:
        """Get full repository name (owner/name)."""
        return self.repo['full_name']

    def get_clone_url(self) -> str:
        """Get the clone URL for this repository."""
        if self.clone_url_getter:
            return self.clone_url_getter(self.repo)
        return self.repo.get('clone_url', self.repo.get('ssh_url'))

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a variable from the context."""
        return self.variables.get(name, default)

    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable in the context."""
        self.variables[name] = value

    def add_result(self, result: ActionResult) -> None:
        """Add an action result to the context."""
        self.results.append(result)

    @property
    def last_result(self) -> Optional[ActionResult]:
        """Get the most recent action result."""
        return self.results[-1] if self.results else None

    @property
    def has_failures(self) -> bool:
        """Check if any action has failed."""
        return any(r.failed for r in self.results)

    @property
    def all_success(self) -> bool:
        """Check if all actions were successful."""
        return all(r.success for r in self.results)

    def get_default_variables(self) -> Dict[str, str]:
        """Get default template variables from repo data."""
        return {
            'repo_name': self.repo['name'],
            'repo_full_name': self.repo['full_name'],
            'default_branch': self.repo.get('default_branch', 'main'),
            'description': self.repo.get('description', ''),
            'language': self.repo.get('language', ''),
        }
