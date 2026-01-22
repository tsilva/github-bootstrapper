"""GitHub API client for repository operations."""

import os
import sys
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger('gitfleet')


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, username: str, token: Optional[str] = None):
        """Initialize GitHub client.

        Args:
            username: GitHub username
            token: Optional GitHub personal access token
        """
        self.username = username
        self.token = token
        self.headers = {}

        if token:
            self.headers['Authorization'] = f'token {token}'
            logger.info("Using GitHub token for authentication")
        else:
            logger.info("Using unauthenticated mode (public repos only)")

    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated.

        Returns:
            True if token is available
        """
        return bool(self.token)

    def get_user_orgs(self) -> List[str]:
        """Get all organizations for the user.

        Returns:
            List of organization login names
        """
        url = f"https://api.github.com/users/{self.username}/orgs"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return [org['login'] for org in response.json()]
        return []

    def get_org_repos(self, org: str) -> List[Dict[str, Any]]:
        """Get all repositories for an organization.

        Args:
            org: Organization login name

        Returns:
            List of repository dictionaries
        """
        all_repos = []
        page = 1
        per_page = 100

        while True:
            url = f"https://api.github.com/orgs/{org}/repos?page={page}&per_page={per_page}"
            response = requests.get(url, headers=self.headers)

            if response.status_code != 200:
                logger.warning(f"Failed to get repositories for org {org}: {response.status_code}")
                break

            repos_page = response.json()
            if not repos_page:
                break

            all_repos.extend(repos_page)
            page += 1

        return all_repos

    def get_repos(self) -> List[Dict[str, Any]]:
        """Get all repositories for the user, including org repos.

        Returns:
            List of unique repository dictionaries

        Raises:
            SystemExit: If rate limit exceeded or API request fails
        """
        if self.is_authenticated:
            # When authenticated, use endpoint that gets ALL repos including private ones
            url_template = "https://api.github.com/user/repos?page={}&per_page={}&affiliation=owner,collaborator,organization_member"
        else:
            # Unauthenticated - only public repos
            url_template = f"https://api.github.com/users/{self.username}/repos?page={{}}&per_page={{}}"

        # Fetch repositories with pagination
        all_repos = []
        page = 1
        per_page = 100

        while True:
            url = url_template.format(page, per_page)
            response = requests.get(url, headers=self.headers)

            if response.status_code == 403:
                logger.error("GitHub API rate limit exceeded")
                sys.exit(1)
            elif response.status_code != 200:
                raise Exception(f"Failed to get repositories: {response.status_code}")

            repos_page = response.json()
            if not repos_page:
                break

            all_repos.extend(repos_page)
            page += 1

        # If not authenticated, fetch org repos separately
        if not self.is_authenticated:
            orgs = self.get_user_orgs()
            logger.info(f"Found {len(orgs)} organizations")

            for org in orgs:
                org_repos = self.get_org_repos(org)
                logger.info(f"Found {len(org_repos)} repositories in organization {org}")
                all_repos.extend(org_repos)

        # Deduplicate repos based on id
        unique_repos = {repo['id']: repo for repo in all_repos}.values()
        logger.info(f"Found {len(unique_repos)} unique repositories total")
        return list(unique_repos)

    def get_clone_url(self, repo: Dict[str, Any]) -> str:
        """Get the appropriate clone URL based on authentication.

        Args:
            repo: Repository dictionary from GitHub API

        Returns:
            Clone URL (SSH if authenticated, HTTPS otherwise)
        """
        if self.is_authenticated:
            # Use SSH URL when token is available
            return repo['ssh_url']
        return repo['clone_url']
