"""Core reusable predicates for repository operations."""

import os
from typing import Tuple, TYPE_CHECKING

from .base import Predicate

if TYPE_CHECKING:
    from ..core.types import RepoContext


class RepoExists(Predicate):
    """Check if repository exists locally."""

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        exists = os.path.exists(ctx.repo_path) and os.path.isdir(ctx.repo_path)
        if exists:
            return True, "Repository exists locally"
        return False, "Repository doesn't exist locally"


class RepoClean(Predicate):
    """Check if repository has no unstaged changes."""

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        from ..utils.git import has_unstaged_changes

        if not os.path.exists(ctx.repo_path):
            return False, "Repository doesn't exist locally"

        if has_unstaged_changes(ctx.repo_path):
            return False, "Repository has unstaged changes"
        return True, "Repository is clean"


class NotArchived(Predicate):
    """Check if repository is not archived."""

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        if ctx.repo.get('archived', False):
            return False, "Repository is archived"
        return True, "Repository is not archived"


class NotFork(Predicate):
    """Check if repository is not a fork."""

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        if ctx.repo.get('fork', False):
            return False, "Repository is a fork"
        return True, "Repository is not a fork"


class IsPrivate(Predicate):
    """Check if repository is private."""

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        if ctx.repo.get('private', False):
            return True, "Repository is private"
        return False, "Repository is public"


class IsPublic(Predicate):
    """Check if repository is public."""

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        if not ctx.repo.get('private', False):
            return True, "Repository is public"
        return False, "Repository is private"


class FileExists(Predicate):
    """Check if a file exists in the repository."""

    def __init__(self, path: str):
        """Initialize with relative file path.

        Args:
            path: Relative path from repository root
        """
        self.path = path

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        full_path = os.path.join(ctx.repo_path, self.path)
        if os.path.exists(full_path):
            return True, f"File {self.path} exists"
        return False, f"File {self.path} doesn't exist"


class FileNotExists(Predicate):
    """Check if a file does not exist in the repository."""

    def __init__(self, path: str):
        """Initialize with relative file path.

        Args:
            path: Relative path from repository root
        """
        self.path = path

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        full_path = os.path.join(ctx.repo_path, self.path)
        if not os.path.exists(full_path):
            return True, f"File {self.path} doesn't exist"
        return False, f"File {self.path} already exists"


class DirectoryExists(Predicate):
    """Check if a directory exists in the repository."""

    def __init__(self, path: str):
        """Initialize with relative directory path.

        Args:
            path: Relative path from repository root
        """
        self.path = path

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        full_path = os.path.join(ctx.repo_path, self.path)
        if os.path.isdir(full_path):
            return True, f"Directory {self.path} exists"
        return False, f"Directory {self.path} doesn't exist"


class HasLanguage(Predicate):
    """Check if repository has a specific primary language."""

    def __init__(self, language: str):
        """Initialize with language name.

        Args:
            language: Language name (case-insensitive)
        """
        self.language = language.lower()

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        repo_lang = ctx.repo.get('language', '') or ''
        if repo_lang.lower() == self.language:
            return True, f"Repository uses {repo_lang}"
        return False, f"Repository doesn't use {self.language}"


class NameMatches(Predicate):
    """Check if repository name matches a glob pattern."""

    def __init__(self, pattern: str):
        """Initialize with glob pattern.

        Args:
            pattern: Glob pattern to match against repo name
        """
        self.pattern = pattern

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        import fnmatch
        if fnmatch.fnmatch(ctx.repo_name, self.pattern):
            return True, f"Name matches pattern {self.pattern}"
        return False, f"Name doesn't match pattern {self.pattern}"


class OwnerIs(Predicate):
    """Check if repository owner matches."""

    def __init__(self, owner: str):
        """Initialize with owner name.

        Args:
            owner: Owner/organization name
        """
        self.owner = owner

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        repo_owner = ctx.repo.get('owner', {}).get('login', '')
        if repo_owner == self.owner:
            return True, f"Owner is {self.owner}"
        return False, f"Owner is {repo_owner}, not {self.owner}"


class HasGitDirectory(Predicate):
    """Check if path has a .git directory (is a git repo)."""

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        git_path = os.path.join(ctx.repo_path, '.git')
        if os.path.isdir(git_path):
            return True, "Is a git repository"
        return False, "Not a git repository"


class ForceEnabled(Predicate):
    """Check if force mode is enabled in context."""

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        if ctx.force:
            return True, "Force mode enabled"
        return False, "Force mode not enabled"


# Pre-built common predicate combinations
REPO_EXISTS_AND_CLEAN = RepoExists() & RepoClean()
ACTIVE_REPO = NotArchived() & NotFork() & RepoExists()
