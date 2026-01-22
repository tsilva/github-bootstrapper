"""Execute Claude prompts across repositories using templates or raw prompts."""

import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from .base import Operation, OperationResult, OperationStatus
from ..prompt_templates import template_registry, RawPromptTemplate

logger = logging.getLogger('gitfleet')


class ClaudeExecOperation(Operation):
    """Execute Claude prompts using templates or raw prompts."""

    name = "claude-exec"
    description = "Execute Claude prompts using templates or raw prompts"
    requires_token = False
    safe_parallel = False  # Sequential for Claude API rate limits
    show_progress_only = True  # Show progress bar instead of individual logs

    def __init__(
        self,
        base_dir: str,
        dry_run: bool = False,
        prompt: str = "",
        force: bool = False,
        yes: bool = False,
        clone_url_getter=None
    ):
        """Initialize claude-exec operation.

        Args:
            base_dir: Base directory for repositories
            dry_run: If True, don't actually execute operations
            prompt: Template name or raw prompt string
            force: If True, skip should_run() checks (run on all repos)
            yes: If True, skip confirmation prompt
            clone_url_getter: Ignored (for compatibility)
        """
        super().__init__(base_dir, dry_run)
        self.prompt_input = prompt
        self.force = force
        self.yes = yes

        # Resolve template or create raw template
        template_class = template_registry.get(prompt)
        if template_class:
            self.template = template_class()
            self.is_builtin = True
        else:
            self.template = RawPromptTemplate(prompt)
            self.is_builtin = False

    def should_skip(self, repo: Dict, repo_path: str) -> Optional[str]:
        """Check if operation should be skipped for this repository.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local filesystem path to repository

        Returns:
            Skip reason string if should skip, None otherwise
        """
        if self.force:
            # Force mode: only skip if repo doesn't exist
            from ..prompt_templates.base import repo_exists
            if not repo_exists(repo_path):
                return "Repository doesn't exist locally"
            return None

        # Use template's should_run logic
        should_run, reason = self.template.should_run(repo, repo_path)
        if not should_run:
            return reason

        return None

    def pre_batch_hook(
        self,
        repos_to_execute: List[Dict],
        repos_skipped: List[Tuple[Dict, str]],
        base_dir: str,
        dry_run: bool
    ) -> None:
        """Show execution briefing and get user confirmation.

        Args:
            repos_to_execute: List of repositories that will be processed
            repos_skipped: List of (repo, skip_reason) tuples for skipped repos
            base_dir: Base directory for repositories
            dry_run: Whether this is a dry run
        """
        # Display briefing
        print("\n" + "=" * 60)
        print("CLAUDE EXECUTION BRIEFING")
        print("=" * 60)

        if self.is_builtin:
            print(f"Template: {self.template.name}")
            print(f"Description: {self.template.description}")
        else:
            print("Mode: Raw prompt")

        print(f"\nPrompt: {self.template.prompt}")

        # Show repos to execute (use repos_to_execute directly)
        print(f"\nRepositories to execute: {len(repos_to_execute)}")
        if repos_to_execute:
            for repo in repos_to_execute[:10]:  # Show first 10
                print(f"  ✓ {repo['full_name']}")
            if len(repos_to_execute) > 10:
                print(f"  ... and {len(repos_to_execute) - 10} more")

        # Show skipped repos count only (no details during briefing)
        if repos_skipped:
            print(f"\nRepositories to skip: {len(repos_skipped)}")
            if dry_run:
                # In dry-run mode, show details
                for repo, reason in repos_skipped[:10]:
                    print(f"  ⊘ {repo['full_name']} - {reason}")
                if len(repos_skipped) > 10:
                    print(f"  ... and {len(repos_skipped) - 10} more")
            else:
                print(f"  (run with --dry-run to see details)")

        print("=" * 60)

        # Ask for confirmation unless --yes flag or dry-run
        if not self.yes and not dry_run:
            import sys
            # When stdin is piped, read from /dev/tty to get user input
            if sys.stdin.isatty():
                response = input("\nProceed with execution? [y/N]: ")
            else:
                try:
                    with open('/dev/tty', 'r') as tty:
                        print("\nProceed with execution? [y/N]: ", end='', flush=True)
                        response = tty.readline().strip()
                except OSError:
                    # /dev/tty not available (e.g., non-interactive environment)
                    print("\nNo TTY available for confirmation. Use --yes flag to skip prompt.")
                    sys.exit(1)
            if response.lower() != 'y':
                print("Execution cancelled.")
                sys.exit(0)

    def execute(self, repo: Dict, repo_path: str) -> OperationResult:
        """Execute Claude CLI with the template prompt.

        Args:
            repo: Repository dictionary from GitHub API
            repo_path: Local filesystem path to repository

        Returns:
            OperationResult indicating success/failure/skip
        """
        repo_name = repo['name']
        repo_full_name = repo['full_name']

        # Handle dry run
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute prompt on {repo_name}")
            return OperationResult(
                status=OperationStatus.SUCCESS,
                message="Dry run: Would execute prompt",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )

        # Get variables and substitute in prompt
        variables = self.template.get_variables(repo, repo_path)
        prompt_text = self.template.prompt
        for var_name, var_value in variables.items():
            prompt_text = prompt_text.replace(f"{{{{{var_name}}}}}", str(var_value))

        # Execute Claude CLI
        try:
            cmd = [
                'claude',
                '-p', prompt_text,
                '--permission-mode', 'acceptEdits',
                '--output-format', 'json'
            ]

            logger.info(f"Executing Claude on {repo_name}...")

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )

            if result.returncode == 0:
                logger.info(f"Successfully executed on {repo_name}")
                return OperationResult(
                    status=OperationStatus.SUCCESS,
                    message="Prompt executed successfully",
                    repo_name=repo_name,
                    repo_full_name=repo_full_name
                )
            else:
                error = result.stderr or result.stdout
                logger.error(f"Failed on {repo_name}: {error[:200]}")
                return OperationResult(
                    status=OperationStatus.FAILED,
                    message=f"Claude CLI failed: {error[:100]}",
                    repo_name=repo_name,
                    repo_full_name=repo_full_name
                )

        except subprocess.TimeoutExpired:
            logger.error(f"Execution timed out for {repo_name}")
            return OperationResult(
                status=OperationStatus.FAILED,
                message="Operation timed out (5 minutes)",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )
        except FileNotFoundError:
            logger.error("Claude CLI not found. Please ensure Claude Code is installed.")
            return OperationResult(
                status=OperationStatus.FAILED,
                message="Claude CLI not found",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )
        except Exception as e:
            logger.error(f"Failed to execute on {repo_name}: {e}")
            return OperationResult(
                status=OperationStatus.FAILED,
                message=f"Unexpected error: {str(e)}",
                repo_name=repo_name,
                repo_full_name=repo_full_name
            )
