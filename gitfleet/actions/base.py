"""Base class for actions."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.types import RepoContext, ActionResult


class Action(ABC):
    """Base class for actions that perform operations on repositories.

    Actions are single-responsibility units of work that can be composed
    into pipelines. Each action should do one thing well.
    """

    # Name used for logging and identification
    name: str = "base"
    # Whether this action modifies the repository (affects dry-run behavior)
    modifies_repo: bool = True
    # Description of what this action does
    description: str = "Base action"

    @abstractmethod
    def execute(self, ctx: 'RepoContext') -> 'ActionResult':
        """Execute the action on a repository.

        Args:
            ctx: Repository context with all necessary data

        Returns:
            ActionResult indicating success/failure/skip
        """
        pass

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        """Get the message to display in dry-run mode.

        Override this to provide a more specific message.

        Args:
            ctx: Repository context

        Returns:
            Message describing what would happen
        """
        return f"Would execute {self.name}"
