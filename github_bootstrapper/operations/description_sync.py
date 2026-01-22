"""Description-sync operation: sync GitHub repo description with README tagline."""

import os
import re
import subprocess
import logging
from typing import Dict, Any, Optional
from .base import Operation, OperationResult, OperationStatus
from ..utils.git import repo_exists

logger = logging.getLogger('github_bootstrapper')

# GitHub description character limit
MAX_DESCRIPTION_LENGTH = 350


class DescriptionSyncOperation(Operation):
    """Description-sync operation: sync GitHub repo description with README tagline."""

    name = "description-sync"
    description = "Sync GitHub repo description with README tagline"
    requires_token = False  # gh CLI handles its own auth
    safe_parallel = True    # Independent CLI calls per repo

    def __init__(
        self,
        base_dir: str,
        dry_run: bool = False,
        clone_url_getter=None
    ):
        """Initialize description-sync operation.

        Args:
            base_dir: Base directory for repositories
            dry_run: If True, don't actually execute operations
            clone_url_getter: Ignored (for compatibility with operation framework)
        """
        super().__init__(base_dir, dry_run)

    def _extract_tagline(self, readme_path: str) -> Optional[str]:
        """Extract tagline from README.md.

        Tries multiple patterns in priority order:
        1. Bold text (**...**) within <div align="center"> block
        2. First paragraph after # Title

        Args:
            readme_path: Path to README.md file

        Returns:
            Extracted tagline or None if not found
        """
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            logger.debug(f"Failed to read README: {e}")
            return None

        # Pattern 1: Bold text in centered div
        # Match <div ... align="center" ...> ... **tagline** ... </div>
        div_pattern = r'<div[^>]*align=["\']?center["\']?[^>]*>(.*?)</div>'
        div_match = re.search(div_pattern, content, re.DOTALL | re.IGNORECASE)

        if div_match:
            div_content = div_match.group(1)
            # Find bold text within the div (last one is typically the tagline)
            bold_matches = re.findall(r'\*\*([^*]+)\*\*', div_content)
            if bold_matches:
                # Filter out matches that are likely badges or links
                for tagline in bold_matches:
                    # Skip very short text or text with URLs/badges
                    if len(tagline) > 15 and 'http' not in tagline.lower():
                        return tagline.strip()

        # Pattern 2: First paragraph after # Title
        # Match: # Title\n\n<first paragraph>
        title_pattern = r'^#\s+[^\n]+\n\n([^\n#]+)'
        title_match = re.search(title_pattern, content, re.MULTILINE)

        if title_match:
            paragraph = title_match.group(1).strip()
            # Ensure it's substantial text, not badges or links
            if len(paragraph) > 20 and not paragraph.startswith('[') and not paragraph.startswith('<'):
                return paragraph

        return None

    def _truncate_description(self, description: str) -> str:
        """Truncate description to GitHub's limit.

        Args:
            description: Original description

        Returns:
            Truncated description (with ... if truncated)
        """
        if len(description) <= MAX_DESCRIPTION_LENGTH:
            return description
        return description[:MAX_DESCRIPTION_LENGTH - 3].rstrip() + "..."

    def _update_description(self, repo_full_name: str, new_description: str) -> tuple[bool, str]:
        """Update GitHub repo description using gh CLI.

        Args:
            repo_full_name: Full repository name (owner/repo)
            new_description: New description to set

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["gh", "repo", "edit", repo_full_name, "-d", new_description],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, "Description updated successfully"
            else:
                error = result.stderr or result.stdout
                return False, f"gh command failed: {error.strip()}"

        except subprocess.TimeoutExpired:
            return False, "gh command timed out"
        except FileNotFoundError:
            return False, "gh CLI not found - please install GitHub CLI"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def execute(self, repo: Dict[str, Any], repo_path: str) -> OperationResult:
        """Execute description-sync operation on a repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            OperationResult indicating success/failure/skip
        """
        repo_name = repo['name']
        repo_full_name = repo['full_name']

        # Check if should skip
        skip_reason = self.should_skip(repo, repo_path)
        if skip_reason:
            logger.info(f"Skipping {repo_name}: {skip_reason}")
            return OperationResult(
                status=OperationStatus.SKIPPED,
                message=skip_reason,
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Read README and extract tagline
        readme_path = os.path.join(repo_path, 'README.md')
        tagline = self._extract_tagline(readme_path)

        if not tagline:
            logger.info(f"Skipping {repo_name}: No tagline found in README")
            return OperationResult(
                status=OperationStatus.SKIPPED,
                message="No tagline found in README",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Truncate if necessary
        tagline = self._truncate_description(tagline)

        # Check if description already matches
        current_description = repo.get('description') or ''
        if tagline == current_description:
            logger.info(f"Skipping {repo_name}: Description already matches tagline")
            return OperationResult(
                status=OperationStatus.SKIPPED,
                message="Description already matches tagline",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Handle dry run
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update {repo_name} description:")
            logger.info(f"  Current: {current_description[:80]}..." if len(current_description) > 80 else f"  Current: {current_description}")
            logger.info(f"  New:     {tagline[:80]}..." if len(tagline) > 80 else f"  New:     {tagline}")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message=f"Dry run: Would update description",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Update the description
        success, message = self._update_description(repo_full_name, tagline)

        if success:
            logger.info(f"Updated description for {repo_name}")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message="Description synced with README tagline",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )
        else:
            logger.error(f"Failed to update {repo_name}: {message}")
            return OperationResult(
                status=OperationStatus.FAILED,
                message=message,
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

    def should_skip(self, repo: Dict[str, Any], repo_path: str) -> Optional[str]:
        """Check if description-sync should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local path to the repository

        Returns:
            Skip reason if should skip, None otherwise
        """
        # Skip archived repos (can't update)
        if repo.get('archived', False):
            return "Repository is archived"

        # Skip if repo doesn't exist locally
        if not repo_exists(repo_path):
            return "Repository doesn't exist locally"

        # Skip if no README.md
        readme_path = os.path.join(repo_path, 'README.md')
        if not os.path.exists(readme_path):
            return "No README.md found"

        return None
