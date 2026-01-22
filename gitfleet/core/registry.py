"""Unified generic registry for auto-discovery of classes."""

import pkgutil
import importlib
import inspect
import logging
from typing import Dict, Type, TypeVar, Generic, List, Optional

logger = logging.getLogger('gitfleet')

T = TypeVar('T')


class Registry(Generic[T]):
    """Generic registry for discovering and managing classes.

    This unified registry replaces the separate OperationRegistry and
    TemplateRegistry with a single, configurable implementation.

    Example usage:
        # For operations
        operation_registry = Registry(
            base_class=Operation,
            package='gitfleet.operations',
            exclude=['base', 'registry']
        )

        # For templates
        template_registry = Registry(
            base_class=PromptTemplate,
            package='gitfleet.prompt_templates',
            exclude=['base', 'registry', 'raw']
        )
    """

    def __init__(
        self,
        base_class: Type[T],
        package: str,
        exclude: Optional[List[str]] = None,
        name_attr: str = 'name',
        base_name: str = 'base'
    ):
        """Initialize the registry.

        Args:
            base_class: The base class that registered items must inherit from
            package: The package path to scan for classes (e.g., 'gitfleet.operations')
            exclude: Module names to exclude from scanning
            name_attr: Attribute name used to identify items (default: 'name')
            base_name: Value of name_attr that indicates the base class (default: 'base')
        """
        self._base_class = base_class
        self._package = package
        self._exclude = set(exclude or [])
        self._name_attr = name_attr
        self._base_name = base_name
        self._items: Dict[str, Type[T]] = {}
        self._discover()

    def _discover(self) -> None:
        """Discover all classes in the package."""
        try:
            package_module = importlib.import_module(self._package)
        except ImportError as e:
            logger.warning(f"Failed to import package {self._package}: {e}")
            return

        package_path = getattr(package_module, '__path__', None)
        if package_path is None:
            logger.warning(f"Package {self._package} has no __path__")
            return

        # Iterate through all modules in the package
        for _, module_name, _ in pkgutil.iter_modules(package_path):
            if module_name in self._exclude:
                continue

            try:
                module = importlib.import_module(f'{self._package}.{module_name}')
                self._scan_module(module)
            except Exception as e:
                logger.warning(f"Failed to load module {module_name}: {e}")

    def _scan_module(self, module) -> None:
        """Scan a module for registerable classes."""
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, self._base_class):
                continue
            if obj is self._base_class:
                continue
            if not hasattr(obj, self._name_attr):
                continue

            item_name = getattr(obj, self._name_attr)
            if item_name == self._base_name:
                continue

            self._items[item_name] = obj
            logger.debug(f"Registered {self._base_class.__name__}: {item_name}")

    def get(self, name: str) -> Optional[Type[T]]:
        """Get an item by name.

        Args:
            name: Item name

        Returns:
            Item class or None if not found
        """
        return self._items.get(name)

    def get_or_raise(self, name: str) -> Type[T]:
        """Get an item by name, raising if not found.

        Args:
            name: Item name

        Returns:
            Item class

        Raises:
            KeyError: If item not found
        """
        if name not in self._items:
            available = ', '.join(sorted(self._items.keys()))
            raise KeyError(f"Unknown {self._base_class.__name__}: {name}. Available: {available}")
        return self._items[name]

    def list_names(self) -> List[str]:
        """Get list of available item names.

        Returns:
            Sorted list of item names
        """
        return sorted(self._items.keys())

    def get_all(self) -> Dict[str, Type[T]]:
        """Get all registered items.

        Returns:
            Dictionary mapping names to classes
        """
        return self._items.copy()

    def register(self, item_class: Type[T]) -> None:
        """Manually register an item.

        Args:
            item_class: Class to register
        """
        if not hasattr(item_class, self._name_attr):
            raise ValueError(f"Class must have '{self._name_attr}' attribute")
        name = getattr(item_class, self._name_attr)
        self._items[name] = item_class

    def __contains__(self, name: str) -> bool:
        """Check if an item is registered."""
        return name in self._items

    def __len__(self) -> int:
        """Get number of registered items."""
        return len(self._items)

    def __iter__(self):
        """Iterate over registered item names."""
        return iter(self._items)
