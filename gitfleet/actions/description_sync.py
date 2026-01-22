"""Description sync action."""

import os
import re
import subprocess
import logging
from typing import Optional, TYPE_CHECKING

from .base import Action
from ..core.types import ActionResult, Status

if TYPE_CHECKING:
    from ..core.types import RepoContext

logger = logging.getLogger('gitfleet')

# GitHub description character limit
MAX_DESCRIPTION_LENGTH = 350


def extract_tagline(readme_path: str) -> Optional[str]:
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
    div_pattern = r'<div[^>]*align=["\']?center["\']?[^>]*>(.*?)</div>'
    div_match = re.search(div_pattern, content, re.DOTALL | re.IGNORECASE)

    if div_match:
        div_content = div_match.group(1)
        # Find bold text within the div
        bold_matches = re.findall(r'\*\*([^*]+)\*\*', div_content)
        if bold_matches:
            for tagline in bold_matches:
                # Skip very short text or text with URLs/badges
                if len(tagline) > 15 and 'http' not in tagline.lower():
                    return tagline.strip()

    # Pattern 2: First paragraph after # Title
    title_pattern = r'^#\s+[^\n]+\n\n([^\n#]+)'
    title_match = re.search(title_pattern, content, re.MULTILINE)

    if title_match:
        paragraph = title_match.group(1).strip()
        if len(paragraph) > 20 and not paragraph.startswith('[') and not paragraph.startswith('<'):
            return paragraph

    return None


def truncate_description(description: str, max_length: int = MAX_DESCRIPTION_LENGTH) -> str:
    """Truncate description to GitHub's limit.

    Args:
        description: Original description
        max_length: Maximum length

    Returns:
        Truncated description (with ... if truncated)
    """
    if len(description) <= max_length:
        return description
    return description[:max_length - 3].rstrip() + "..."


class DescriptionSyncAction(Action):
    """Sync GitHub repo description with README tagline."""

    name = "description-sync"
    modifies_repo = True  # Modifies GitHub state
    description = "Sync repo description with README tagline"

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Execute description sync."""
        readme_path = os.path.join(ctx.repo_path, 'README.md')

        # Extract tagline
        tagline = extract_tagline(readme_path)
        if not tagline:
            return ActionResult(
                status=Status.SKIPPED,
                message="No tagline found in README",
                action_name=self.name
            )

        # Truncate if necessary
        tagline = truncate_description(tagline)

        # Check if description already matches
        current_description = ctx.repo.get('description') or ''
        if tagline == current_description:
            return ActionResult(
                status=Status.SKIPPED,
                message="Description already matches tagline",
                action_name=self.name
            )

        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={
                    'dry_run': True,
                    'current': current_description,
                    'new': tagline
                }
            )

        # Update the description via gh CLI
        try:
            result = subprocess.run(
                ["gh", "repo", "edit", ctx.repo_full_name, "-d", tagline],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return ActionResult(
                    status=Status.SUCCESS,
                    message="Description synced with README tagline",
                    action_name=self.name,
                    metadata={'new_description': tagline}
                )
            else:
                error = result.stderr or result.stdout
                return ActionResult(
                    status=Status.FAILED,
                    message=f"gh command failed: {error.strip()}",
                    action_name=self.name
                )

        except subprocess.TimeoutExpired:
            return ActionResult(
                status=Status.FAILED,
                message="gh command timed out",
                action_name=self.name
            )
        except FileNotFoundError:
            return ActionResult(
                status=Status.FAILED,
                message="gh CLI not found - please install GitHub CLI",
                action_name=self.name
            )
        except Exception as e:
            return ActionResult(
                status=Status.FAILED,
                message=f"Unexpected error: {e}",
                action_name=self.name
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would update description for {ctx.repo_name}"
