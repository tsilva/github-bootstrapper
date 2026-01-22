"""JSON file manipulation actions."""

import os
import json
import logging
from typing import Dict, Any, TYPE_CHECKING

from .base import Action
from ..core.types import ActionResult, Status

if TYPE_CHECKING:
    from ..core.types import RepoContext

logger = logging.getLogger('gitfleet')


def deep_merge(base: Dict, patch: Dict) -> Dict:
    """Deep merge patch into base dict.

    Args:
        base: Base dictionary
        patch: Dictionary to merge in

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in patch.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class JsonPatchAction(Action):
    """Patch a JSON file with specified values."""

    name = "json-patch"
    modifies_repo = True
    description = "Patch JSON file with values"

    def __init__(self, path: str, patch: Dict[str, Any], create_if_missing: bool = True):
        """Initialize JSON patch action.

        Args:
            path: Relative path to JSON file from repo root
            patch: Dictionary of values to merge into JSON
            create_if_missing: Create file if it doesn't exist
        """
        self.path = path
        self.patch = patch
        self.create_if_missing = create_if_missing

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Patch the JSON file."""
        full_path = os.path.join(ctx.repo_path, self.path)

        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True, 'path': self.path}
            )

        try:
            # Create directory if needed
            dir_path = os.path.dirname(full_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # Read existing or create new
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    data = json.load(f)
                created = False
            elif self.create_if_missing:
                data = {}
                created = True
            else:
                return ActionResult(
                    status=Status.SKIPPED,
                    message=f"File {self.path} doesn't exist",
                    action_name=self.name,
                    metadata={'path': self.path}
                )

            # Apply patch
            new_data = deep_merge(data, self.patch)

            # Write back
            with open(full_path, 'w') as f:
                json.dump(new_data, f, indent=2)

            action_msg = "Created and patched" if created else "Patched"
            return ActionResult(
                status=Status.SUCCESS,
                message=f"{action_msg} {self.path}",
                action_name=self.name,
                metadata={'path': self.path, 'created': created}
            )

        except Exception as e:
            logger.error(f"Failed to patch {self.path}: {e}")
            return ActionResult(
                status=Status.FAILED,
                message=f"Failed to patch {self.path}: {e}",
                action_name=self.name,
                metadata={'path': self.path, 'error': str(e)}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would patch {self.path}"


class JsonReadAction(Action):
    """Read a JSON file and store in context variables."""

    name = "json-read"
    modifies_repo = False
    description = "Read JSON file into context"

    def __init__(self, path: str, variable_name: str):
        """Initialize JSON read action.

        Args:
            path: Relative path to JSON file from repo root
            variable_name: Name to store the data in context.variables
        """
        self.path = path
        self.variable_name = variable_name

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Read the JSON file."""
        full_path = os.path.join(ctx.repo_path, self.path)

        try:
            if not os.path.exists(full_path):
                return ActionResult(
                    status=Status.SKIPPED,
                    message=f"File {self.path} doesn't exist",
                    action_name=self.name,
                    metadata={'path': self.path}
                )

            with open(full_path, 'r') as f:
                data = json.load(f)

            ctx.set_variable(self.variable_name, data)

            return ActionResult(
                status=Status.SUCCESS,
                message=f"Read {self.path}",
                action_name=self.name,
                metadata={'path': self.path, 'variable': self.variable_name}
            )

        except Exception as e:
            return ActionResult(
                status=Status.FAILED,
                message=f"Failed to read {self.path}: {e}",
                action_name=self.name,
                metadata={'path': self.path, 'error': str(e)}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would read {self.path}"
