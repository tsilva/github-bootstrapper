"""Claude prompt templates for github-bootstrapper."""

from .registry import template_registry
from .base import PromptTemplate
from .raw import RawPromptTemplate

__all__ = ['template_registry', 'PromptTemplate', 'RawPromptTemplate']
