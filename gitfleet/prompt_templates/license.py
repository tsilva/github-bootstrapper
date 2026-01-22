"""License template for MIT LICENSE generation."""

import os
from datetime import datetime
from typing import Dict, Tuple
from .base import PromptTemplate, repo_exists


class LicenseTemplate(PromptTemplate):
    """Add MIT LICENSE file to repositories."""

    name = "license"
    description = "Add MIT LICENSE file to repositories"
    prompt = """Create an MIT LICENSE file in the root of this repository.

Use the following details:
- Year: {{year}}
- Copyright holder: {{license_author}}

The MIT LICENSE should be the standard format with the copyright line:
"Copyright (c) {{year}} {{license_author}}"

Create the file as LICENSE (no extension)."""

    def should_run(self, repo: Dict, repo_path: str) -> Tuple[bool, str]:
        """Skip archived repos, repos with existing LICENSE, or missing LICENSE_AUTHOR.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local filesystem path to repository

        Returns:
            (should_run, reason) tuple
        """
        if not repo_exists(repo_path):
            return False, "Repository doesn't exist locally"

        if repo.get('archived', False):
            return False, "Repository is archived"

        # Check for LICENSE_AUTHOR environment variable
        license_author = os.environ.get('LICENSE_AUTHOR', '').strip()
        if not license_author:
            return False, "LICENSE_AUTHOR environment variable is not set"

        # Check for existing license files (various common names)
        license_files = ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'license', 'license.md', 'license.txt']
        for license_file in license_files:
            license_path = os.path.join(repo_path, license_file)
            if os.path.exists(license_path):
                return False, f"{license_file} already exists"

        return True, "No LICENSE file found - will create MIT LICENSE"

    def get_variables(self, repo: Dict, repo_path: str) -> Dict[str, str]:
        """Get variables for substitution in prompt.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local filesystem path to repository

        Returns:
            Dictionary of variable name -> value for {{variable}} substitution
        """
        # Get base variables
        variables = super().get_variables(repo, repo_path)

        # Add license-specific variables
        variables['year'] = str(datetime.now().year)
        variables['license_author'] = os.environ.get('LICENSE_AUTHOR', '')

        return variables
