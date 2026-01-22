"""Subprocess-based actions."""

import subprocess
import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from .base import Action
from ..core.types import ActionResult, Status

if TYPE_CHECKING:
    from ..core.types import RepoContext

logger = logging.getLogger('gitfleet')


class SubprocessAction(Action):
    """Run a subprocess command in the repository."""

    name = "subprocess"
    modifies_repo = True
    description = "Run subprocess command"

    def __init__(
        self,
        command: List[str],
        timeout: int = 120,
        capture_output: bool = True,
        check: bool = True,
        shell: bool = False,
        env: Optional[Dict[str, str]] = None
    ):
        """Initialize subprocess action.

        Args:
            command: Command and arguments as list
            timeout: Timeout in seconds
            capture_output: Capture stdout/stderr
            check: Raise on non-zero exit
            shell: Run through shell
            env: Environment variables to add
        """
        self.command = command
        self.timeout = timeout
        self.capture_output = capture_output
        self.check = check
        self.shell = shell
        self.env = env

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Execute the subprocess."""
        import os

        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True, 'command': self.command}
            )

        # Build environment
        env = os.environ.copy()
        if self.env:
            env.update(self.env)

        try:
            result = subprocess.run(
                self.command,
                cwd=ctx.repo_path,
                capture_output=self.capture_output,
                check=self.check,
                timeout=self.timeout,
                shell=self.shell,
                env=env,
                text=True
            )

            return ActionResult(
                status=Status.SUCCESS,
                message=f"Command succeeded: {' '.join(self.command[:2])}...",
                action_name=self.name,
                metadata={
                    'command': self.command,
                    'stdout': result.stdout if self.capture_output else None,
                    'stderr': result.stderr if self.capture_output else None,
                    'returncode': result.returncode
                }
            )

        except subprocess.TimeoutExpired:
            return ActionResult(
                status=Status.FAILED,
                message=f"Command timed out after {self.timeout}s",
                action_name=self.name,
                metadata={'command': self.command, 'timeout': self.timeout}
            )
        except subprocess.CalledProcessError as e:
            return ActionResult(
                status=Status.FAILED,
                message=f"Command failed with exit code {e.returncode}",
                action_name=self.name,
                metadata={
                    'command': self.command,
                    'returncode': e.returncode,
                    'stdout': e.stdout if self.capture_output else None,
                    'stderr': e.stderr if self.capture_output else None
                }
            )
        except Exception as e:
            return ActionResult(
                status=Status.FAILED,
                message=f"Command error: {e}",
                action_name=self.name,
                metadata={'command': self.command, 'error': str(e)}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would run: {' '.join(self.command)}"


class ClaudeCliAction(Action):
    """Run Claude CLI with a prompt."""

    name = "claude-cli"
    modifies_repo = True
    description = "Execute Claude CLI prompt"

    def __init__(self, prompt: str, timeout: int = 300):
        """Initialize Claude CLI action.

        Args:
            prompt: The prompt to send to Claude
            timeout: Timeout in seconds (default 5 minutes)
        """
        self.prompt = prompt
        self.timeout = timeout

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Execute Claude CLI with the prompt."""
        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True, 'prompt_preview': self.prompt[:100]}
            )

        # Build command
        command = [
            "claude",
            "-p", self.prompt,
            "--permission-mode", "acceptEdits",
            "--output-format", "json"
        ]

        try:
            logger.info(f"Running Claude CLI for {ctx.repo_name}...")
            result = subprocess.run(
                command,
                cwd=ctx.repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode == 0:
                return ActionResult(
                    status=Status.SUCCESS,
                    message="Claude CLI completed",
                    action_name=self.name,
                    metadata={
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    }
                )
            else:
                return ActionResult(
                    status=Status.FAILED,
                    message=f"Claude CLI failed with exit code {result.returncode}",
                    action_name=self.name,
                    metadata={
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    }
                )

        except subprocess.TimeoutExpired:
            return ActionResult(
                status=Status.FAILED,
                message=f"Claude CLI timed out after {self.timeout}s",
                action_name=self.name,
                metadata={'timeout': self.timeout}
            )
        except FileNotFoundError:
            return ActionResult(
                status=Status.FAILED,
                message="Claude CLI not found - ensure 'claude' is installed",
                action_name=self.name
            )
        except Exception as e:
            return ActionResult(
                status=Status.FAILED,
                message=f"Claude CLI error: {e}",
                action_name=self.name,
                metadata={'error': str(e)}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        prompt_preview = self.prompt[:50] + "..." if len(self.prompt) > 50 else self.prompt
        return f"Would run Claude CLI with prompt: {prompt_preview}"


class GhCliAction(Action):
    """Run GitHub CLI (gh) command."""

    name = "gh-cli"
    modifies_repo = False  # By default, but specific commands may modify
    description = "Execute GitHub CLI command"

    def __init__(
        self,
        args: List[str],
        timeout: int = 60,
        modifies_repo: bool = False
    ):
        """Initialize GitHub CLI action.

        Args:
            args: Arguments to pass to gh command
            timeout: Timeout in seconds
            modifies_repo: Whether this command modifies the repo
        """
        self.args = args
        self.timeout = timeout
        self._modifies_repo = modifies_repo

    @property
    def modifies_repo(self) -> bool:
        return self._modifies_repo

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Execute gh CLI command."""
        # Handle dry run for modifying commands
        if ctx.dry_run and self._modifies_repo:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True, 'args': self.args}
            )

        command = ["gh"] + self.args

        try:
            result = subprocess.run(
                command,
                cwd=ctx.repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode == 0:
                return ActionResult(
                    status=Status.SUCCESS,
                    message="gh command succeeded",
                    action_name=self.name,
                    metadata={
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'args': self.args
                    }
                )
            else:
                return ActionResult(
                    status=Status.FAILED,
                    message=f"gh command failed: {result.stderr}",
                    action_name=self.name,
                    metadata={
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'args': self.args,
                        'returncode': result.returncode
                    }
                )

        except subprocess.TimeoutExpired:
            return ActionResult(
                status=Status.FAILED,
                message=f"gh command timed out after {self.timeout}s",
                action_name=self.name,
                metadata={'args': self.args, 'timeout': self.timeout}
            )
        except FileNotFoundError:
            return ActionResult(
                status=Status.FAILED,
                message="gh CLI not found - ensure GitHub CLI is installed",
                action_name=self.name
            )
        except Exception as e:
            return ActionResult(
                status=Status.FAILED,
                message=f"gh command error: {e}",
                action_name=self.name,
                metadata={'args': self.args, 'error': str(e)}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        return f"Would run: gh {' '.join(self.args)}"


class ConditionalSkillAction(Action):
    """Invoke a Claude skill conditionally, where Claude evaluates the condition.

    This action invokes a skill via the Claude CLI. Optionally, a natural language
    condition can be provided that Claude will evaluate to determine whether to
    run the skill or skip it.
    """

    name = "conditional-skill"
    modifies_repo = True
    description = "Conditionally invoke Claude skill"

    def __init__(
        self,
        skill: str,
        condition: Optional[str] = None,
        skill_args: str = "",
        skip_message: str = "Condition not met - skipped",
        timeout: int = 300
    ):
        """Initialize conditional skill action.

        Args:
            skill: Skill name (e.g., "readme-generator", "claude-settings-optimizer")
            condition: Natural language condition for Claude to evaluate.
                       If None, skill runs unconditionally.
            skill_args: Arguments to pass to the skill (e.g., "--mode analyze")
            skip_message: Message Claude should return if condition fails
            timeout: Timeout in seconds (default 5 minutes)
        """
        self.skill = skill
        self.condition = condition
        self.skill_args = skill_args
        self.skip_message = skip_message
        self.timeout = timeout

    def _build_prompt(self) -> str:
        """Build the prompt to send to Claude CLI."""
        skill_invocation = f"/{self.skill}"
        if self.skill_args:
            skill_invocation += f" {self.skill_args}"

        if self.condition:
            return f"""First, evaluate this condition: {self.condition}

If the condition is TRUE: Run {skill_invocation}
If the condition is FALSE: Respond ONLY with: {self.skip_message}"""
        else:
            return skill_invocation

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Execute the skill via Claude CLI."""
        prompt = self._build_prompt()

        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={
                    'dry_run': True,
                    'skill': self.skill,
                    'skill_args': self.skill_args,
                    'condition': self.condition,
                    'prompt_preview': prompt[:100]
                }
            )

        # Build command
        command = [
            "claude",
            "-p", prompt,
            "--permission-mode", "acceptEdits",
            "--output-format", "json"
        ]

        try:
            logger.info(f"Running skill /{self.skill} for {ctx.repo_name}...")
            result = subprocess.run(
                command,
                cwd=ctx.repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # Check if the response indicates a skip
            if self.condition and self.skip_message in result.stdout:
                return ActionResult(
                    status=Status.SKIPPED,
                    message=f"Skipped: {self.skip_message}",
                    action_name=self.name,
                    metadata={
                        'skill': self.skill,
                        'condition': self.condition,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                )

            if result.returncode == 0:
                return ActionResult(
                    status=Status.SUCCESS,
                    message=f"Skill /{self.skill} completed",
                    action_name=self.name,
                    metadata={
                        'skill': self.skill,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    }
                )
            else:
                return ActionResult(
                    status=Status.FAILED,
                    message=f"Skill /{self.skill} failed with exit code {result.returncode}",
                    action_name=self.name,
                    metadata={
                        'skill': self.skill,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    }
                )

        except subprocess.TimeoutExpired:
            return ActionResult(
                status=Status.FAILED,
                message=f"Skill /{self.skill} timed out after {self.timeout}s",
                action_name=self.name,
                metadata={'skill': self.skill, 'timeout': self.timeout}
            )
        except FileNotFoundError:
            return ActionResult(
                status=Status.FAILED,
                message="Claude CLI not found - ensure 'claude' is installed",
                action_name=self.name
            )
        except Exception as e:
            return ActionResult(
                status=Status.FAILED,
                message=f"Skill error: {e}",
                action_name=self.name,
                metadata={'skill': self.skill, 'error': str(e)}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        skill_invocation = f"/{self.skill}"
        if self.skill_args:
            skill_invocation += f" {self.skill_args}"
        if self.condition:
            return f"Would run Claude CLI with skill: {skill_invocation} (condition: {self.condition[:50]}...)"
        return f"Would run Claude CLI with skill: {skill_invocation}"
