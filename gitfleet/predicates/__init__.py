"""Predicates package for composable skip logic."""

from .base import (
    Predicate,
    AllOf,
    AnyOf,
    Not,
    all_of,
    any_of,
    not_,
    AlwaysTrue,
    AlwaysFalse,
)

from .core import (
    RepoExists,
    RepoClean,
    NotArchived,
    NotFork,
    IsPrivate,
    IsPublic,
    FileExists,
    FileNotExists,
    DirectoryExists,
    HasLanguage,
    NameMatches,
    OwnerIs,
    HasGitDirectory,
    ForceEnabled,
    HasUncommittedChanges,
    REPO_EXISTS_AND_CLEAN,
    ACTIVE_REPO,
)

__all__ = [
    # Base
    'Predicate',
    'AllOf',
    'AnyOf',
    'Not',
    'all_of',
    'any_of',
    'not_',
    'AlwaysTrue',
    'AlwaysFalse',
    # Core predicates
    'RepoExists',
    'RepoClean',
    'NotArchived',
    'NotFork',
    'IsPrivate',
    'IsPublic',
    'FileExists',
    'FileNotExists',
    'DirectoryExists',
    'HasLanguage',
    'NameMatches',
    'OwnerIs',
    'HasGitDirectory',
    'ForceEnabled',
    'HasUncommittedChanges',
    # Pre-built combinations
    'REPO_EXISTS_AND_CLEAN',
    'ACTIVE_REPO',
]
