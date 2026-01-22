"""Pipeline registry for auto-discovery."""

import logging
from typing import Dict, Type, List, Optional

from .base import Pipeline

logger = logging.getLogger('gitfleet')


class PipelineRegistry:
    """Registry for discovering and managing pipelines.

    Unlike the generic Registry which uses introspection,
    this registry manually registers pipelines for more control.
    """

    def __init__(self):
        """Initialize the registry."""
        self._pipelines: Dict[str, Type[Pipeline]] = {}
        self._register_builtin_pipelines()

    def _register_builtin_pipelines(self) -> None:
        """Register all built-in pipelines."""
        from .git_ops import SyncPipeline, CloneOnlyPipeline, PullOnlyPipeline, CommitPushPipeline
        from .settings_ops import SandboxEnablePipeline, SettingsCleanPipeline
        from .subprocess_ops import DescriptionSyncPipeline, ClaudePipeline
        from .status_ops import StatusPipeline

        # Git operations
        self.register(SyncPipeline)
        self.register(CloneOnlyPipeline)
        self.register(PullOnlyPipeline)
        self.register(CommitPushPipeline)

        # Status operation
        self.register(StatusPipeline)

        # Settings operations
        self.register(SandboxEnablePipeline)
        self.register(SettingsCleanPipeline)

        # Subprocess operations
        self.register(DescriptionSyncPipeline)
        self.register(ClaudePipeline)

    def register(self, pipeline_class: Type[Pipeline]) -> None:
        """Register a pipeline class.

        Args:
            pipeline_class: Pipeline class to register
        """
        # Get name from class (instantiate briefly to get attribute)
        instance = pipeline_class.__new__(pipeline_class)
        Pipeline.__init__(instance)  # Initialize base to get name
        name = getattr(pipeline_class, 'name', None) or instance.name
        self._pipelines[name] = pipeline_class
        logger.debug(f"Registered pipeline: {name}")

    def get(self, name: str) -> Optional[Type[Pipeline]]:
        """Get a pipeline class by name.

        Args:
            name: Pipeline name

        Returns:
            Pipeline class or None if not found
        """
        return self._pipelines.get(name)

    def get_or_raise(self, name: str) -> Type[Pipeline]:
        """Get a pipeline class by name, raising if not found.

        Args:
            name: Pipeline name

        Returns:
            Pipeline class

        Raises:
            KeyError: If pipeline not found
        """
        if name not in self._pipelines:
            available = ', '.join(sorted(self._pipelines.keys()))
            raise KeyError(f"Unknown pipeline: {name}. Available: {available}")
        return self._pipelines[name]

    def list_pipelines(self) -> List[str]:
        """Get list of available pipeline names.

        Returns:
            Sorted list of pipeline names
        """
        return sorted(self._pipelines.keys())

    def get_all_pipelines(self) -> Dict[str, Type[Pipeline]]:
        """Get all registered pipelines.

        Returns:
            Dictionary mapping names to classes
        """
        return self._pipelines.copy()

    def __contains__(self, name: str) -> bool:
        """Check if a pipeline is registered."""
        return name in self._pipelines

    def __len__(self) -> int:
        """Get number of registered pipelines."""
        return len(self._pipelines)


# Global registry instance
pipeline_registry = PipelineRegistry()
