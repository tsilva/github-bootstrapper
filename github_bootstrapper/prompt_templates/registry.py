"""Template registry for auto-discovery."""

import pkgutil
import importlib
import inspect
import logging
from typing import Dict, Type, List, Optional
from .base import PromptTemplate

logger = logging.getLogger('gitfleet')


class TemplateRegistry:
    """Registry for discovering and managing prompt templates."""

    def __init__(self):
        """Initialize the registry."""
        self._templates: Dict[str, Type[PromptTemplate]] = {}
        self._discover_templates()

    def _discover_templates(self) -> None:
        """Discover all template classes in the prompt_templates package."""
        import gitfleet.prompt_templates as templates_package

        # Get the package path
        package_path = templates_package.__path__

        # Iterate through all modules in the package
        for _, module_name, _ in pkgutil.iter_modules(package_path):
            # Skip base, registry, and raw modules (raw is special)
            if module_name in ('base', 'registry', 'raw'):
                continue

            try:
                # Import the module
                module = importlib.import_module(f'gitfleet.prompt_templates.{module_name}')

                # Find all PromptTemplate subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, PromptTemplate) and
                        obj is not PromptTemplate and
                        hasattr(obj, 'name') and
                        obj.name != 'base'):
                        self._templates[obj.name] = obj
                        logger.debug(f"Registered template: {obj.name} ({obj.description})")

            except Exception as e:
                logger.warning(f"Failed to load template module {module_name}: {e}")

    def get(self, name: str) -> Optional[Type[PromptTemplate]]:
        """Get a template class by name.

        Args:
            name: Template name

        Returns:
            Template class or None if not found
        """
        return self._templates.get(name)

    def list_templates(self) -> List[str]:
        """Get list of available template names.

        Returns:
            List of template names
        """
        return sorted(self._templates.keys())

    def get_all_templates(self) -> Dict[str, Type[PromptTemplate]]:
        """Get all registered templates.

        Returns:
            Dictionary mapping template names to classes
        """
        return self._templates.copy()


# Global registry instance
template_registry = TemplateRegistry()
