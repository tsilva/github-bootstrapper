"""Operation registry for auto-discovery."""

import pkgutil
import importlib
import inspect
import logging
from typing import Dict, Type, List
from .base import Operation

logger = logging.getLogger('gitfleet')


class OperationRegistry:
    """Registry for discovering and managing operations."""

    def __init__(self):
        """Initialize the registry."""
        self._operations: Dict[str, Type[Operation]] = {}
        self._discover_operations()

    def _discover_operations(self) -> None:
        """Discover all operation classes in the operations package."""
        import gitfleet.operations as ops_package

        # Get the package path
        package_path = ops_package.__path__

        # Iterate through all modules in the package
        for _, module_name, _ in pkgutil.iter_modules(package_path):
            # Skip base and registry modules
            if module_name in ('base', 'registry'):
                continue

            try:
                # Import the module
                module = importlib.import_module(f'gitfleet.operations.{module_name}')

                # Find all Operation subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, Operation) and
                        obj is not Operation and
                        hasattr(obj, 'name') and
                        obj.name != 'base'):
                        self._operations[obj.name] = obj
                        logger.debug(f"Registered operation: {obj.name} ({obj.description})")

            except Exception as e:
                logger.warning(f"Failed to load operation module {module_name}: {e}")

    def get(self, name: str) -> Type[Operation]:
        """Get an operation class by name.

        Args:
            name: Operation name

        Returns:
            Operation class

        Raises:
            KeyError: If operation not found
        """
        if name not in self._operations:
            raise KeyError(f"Unknown operation: {name}")
        return self._operations[name]

    def list_operations(self) -> List[str]:
        """Get list of available operation names.

        Returns:
            List of operation names
        """
        return sorted(self._operations.keys())

    def get_all_operations(self) -> Dict[str, Type[Operation]]:
        """Get all registered operations.

        Returns:
            Dictionary mapping operation names to classes
        """
        return self._operations.copy()


# Global registry instance
registry = OperationRegistry()
