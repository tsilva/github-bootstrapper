"""Repository filtering utilities."""

import fnmatch
import logging
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger('github_bootstrapper')


class RepoFilter:
    """Filter for selecting repositories based on criteria."""

    def __init__(
        self,
        repo_names: Optional[List[str]] = None,
        org_names: Optional[List[str]] = None,
        patterns: Optional[List[str]] = None,
        include_forks: bool = False,
        include_archived: bool = False,
        private_only: bool = False,
        public_only: bool = False
    ):
        """Initialize repository filter.

        Args:
            repo_names: Specific repository names to include
            org_names: Organization names to filter by
            patterns: Glob patterns for repository names
            include_forks: Include forked repositories (default: False)
            include_archived: Include archived repositories (default: False)
            private_only: Only include private repositories
            public_only: Only include public repositories
        """
        self.repo_names = set(repo_names) if repo_names else None
        self.org_names = set(org_names) if org_names else None
        self.patterns = patterns or []
        self.include_forks = include_forks
        self.include_archived = include_archived
        self.private_only = private_only
        self.public_only = public_only

        # Validate mutually exclusive flags
        if private_only and public_only:
            raise ValueError("Cannot specify both --private-only and --public-only")

    def filter(self, repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter repositories based on criteria.

        Args:
            repos: List of repository dictionaries

        Returns:
            Filtered list of repositories
        """
        filtered = []
        total = len(repos)

        for repo in repos:
            if self._should_include(repo):
                filtered.append(repo)

        logger.info(f"Filtered {total} repositories to {len(filtered)}")
        return filtered

    def _should_include(self, repo: Dict[str, Any]) -> bool:
        """Check if repository should be included.

        Args:
            repo: Repository dictionary

        Returns:
            True if should be included
        """
        # Check specific repo names
        if self.repo_names and repo['name'] not in self.repo_names:
            return False

        # Check organization
        if self.org_names:
            owner = repo.get('owner', {}).get('login', '')
            if owner not in self.org_names:
                return False

        # Check patterns
        if self.patterns:
            matched = False
            for pattern in self.patterns:
                if fnmatch.fnmatch(repo['name'], pattern):
                    matched = True
                    break
            if not matched:
                return False

        # Check fork status
        if not self.include_forks and repo.get('fork', False):
            return False

        # Check archived status
        if not self.include_archived and repo.get('archived', False):
            return False

        # Check visibility
        is_private = repo.get('private', False)
        if self.private_only and not is_private:
            return False
        if self.public_only and is_private:
            return False

        return True

    @property
    def has_filters(self) -> bool:
        """Check if any filters are active.

        Returns:
            True if filters are set
        """
        return any([
            self.repo_names,
            self.org_names,
            self.patterns,
            not self.include_forks,
            not self.include_archived,
            self.private_only,
            self.public_only
        ])
