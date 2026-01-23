"""Claude Agent SDK-based actions.

This module provides action classes that use the claude-agent-sdk package
instead of subprocess calls for better async support, native Python integration,
and improved error handling.
"""

import asyncio
import logging
import time
from typing import Optional, TYPE_CHECKING

from .base import Action
from ..core.types import ActionResult, Status
from ..utils.async_bridge import run_async_with_timeout

if TYPE_CHECKING:
    from ..core.types import RepoContext

logger = logging.getLogger('gitfleet')

# SDK imports with graceful fallback
try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    from claude_agent_sdk.exceptions import CLINotFoundError, ProcessError
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    CLINotFoundError = Exception
    ProcessError = Exception


class ClaudeSDKAction(Action):
    """Run Claude using the claude-agent-sdk.

    This is the SDK-based replacement for ClaudeCliAction. It provides:
    - Native Python objects instead of JSON parsing
    - Better error types with detailed info
    - Cost tracking (total_cost_usd)
    - Streaming support for long operations
    - Future extensibility (hooks, custom tools, MCP)
    """

    name = "claude-sdk"
    modifies_repo = True
    description = "Execute Claude prompt via SDK"

    def __init__(self, prompt: str, timeout: int = 300):
        """Initialize Claude SDK action.

        Args:
            prompt: The prompt to send to Claude
            timeout: Timeout in seconds (default 5 minutes)
        """
        self.prompt = prompt
        self.timeout = timeout

    async def _execute_async(self, ctx: 'RepoContext') -> ActionResult:
        """Execute Claude SDK asynchronously."""
        if not SDK_AVAILABLE:
            logger.error("claude-agent-sdk not installed")
            return ActionResult(
                status=Status.FAILED,
                message="claude-agent-sdk not installed - run: pip install claude-agent-sdk",
                action_name=self.name
            )

        prompt_preview = self.prompt[:100] + '...' if len(self.prompt) > 100 else self.prompt
        logger.info(f"Running Claude SDK for {ctx.repo_name} | timeout: {self.timeout}s | prompt: {prompt_preview}")
        logger.debug(f"Claude SDK cwd: {ctx.repo_path}")
        start_time = time.time()

        try:
            options = ClaudeAgentOptions(
                cwd=ctx.repo_path,
                permission_mode="acceptEdits"
            )

            async def consume_query():
                """Consume async iterator and return result."""
                async for message in query(prompt=self.prompt, options=options):
                    if hasattr(message, 'result'):
                        return message.result, getattr(message, 'total_cost_usd', None)
                return None, None

            # query() returns an AsyncIterator[Message], must iterate to get results
            result_text, cost = await asyncio.wait_for(consume_query(), timeout=self.timeout)

            duration = time.time() - start_time
            logger.debug(f"Claude SDK completed for {ctx.repo_name} | duration: {duration:.1f}s")

            return ActionResult(
                status=Status.SUCCESS,
                message="Claude SDK completed",
                action_name=self.name,
                metadata={
                    'result': result_text[:5000] if result_text else None,
                    'cost_usd': cost,
                    'duration': duration
                }
            )

        except CLINotFoundError:
            logger.error(f"Claude CLI not found for {ctx.repo_name} | ensure 'claude' is installed and in PATH")
            return ActionResult(
                status=Status.FAILED,
                message="Claude CLI not found - ensure 'claude' is installed",
                action_name=self.name
            )
        except ProcessError as e:
            duration = time.time() - start_time
            logger.debug(f"Claude SDK failed for {ctx.repo_name} | duration: {duration:.1f}s | error: {e}")
            return ActionResult(
                status=Status.FAILED,
                message=f"Claude process error: {e}",
                action_name=self.name,
                metadata={
                    'error': str(e),
                    'exit_code': getattr(e, 'exit_code', None),
                    'stderr': getattr(e, 'stderr', None)
                }
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Claude SDK timed out after {self.timeout}s for {ctx.repo_name} | "
                f"prompt: {prompt_preview} | cwd: {ctx.repo_path}"
            )
            return ActionResult(
                status=Status.FAILED,
                message=f"Claude SDK timed out after {self.timeout}s",
                action_name=self.name,
                metadata={'timeout': self.timeout, 'repo': ctx.repo_name, 'prompt': self.prompt}
            )
        except Exception as e:
            logger.error(f"Claude SDK error for {ctx.repo_name} | prompt: {prompt_preview} | error: {e}", exc_info=True)
            return ActionResult(
                status=Status.FAILED,
                message=f"Claude SDK error: {e}",
                action_name=self.name,
                metadata={'error': str(e)}
            )

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Execute Claude SDK with the prompt."""
        # Handle dry run
        if ctx.dry_run:
            return ActionResult(
                status=Status.SUCCESS,
                message=self.dry_run_message(ctx),
                action_name=self.name,
                metadata={'dry_run': True, 'prompt_preview': self.prompt[:100]}
            )

        # Run async code from sync context with timeout
        try:
            return run_async_with_timeout(
                self._execute_async(ctx),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            prompt_preview = self.prompt[:100] + '...' if len(self.prompt) > 100 else self.prompt
            logger.error(
                f"Claude SDK timed out after {self.timeout}s for {ctx.repo_name} | "
                f"prompt: {prompt_preview} | cwd: {ctx.repo_path}"
            )
            return ActionResult(
                status=Status.FAILED,
                message=f"Claude SDK timed out after {self.timeout}s",
                action_name=self.name,
                metadata={'timeout': self.timeout, 'repo': ctx.repo_name, 'prompt': self.prompt}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        prompt_preview = self.prompt[:50] + "..." if len(self.prompt) > 50 else self.prompt
        return f"Would run Claude SDK with prompt: {prompt_preview}"


class ConditionalSkillSDKAction(Action):
    """Invoke a Claude skill conditionally using the SDK.

    This is the SDK-based replacement for ConditionalSkillAction. It optionally
    evaluates a natural language condition to determine whether to run the skill.
    """

    name = "conditional-skill-sdk"
    modifies_repo = True
    description = "Conditionally invoke Claude skill via SDK"

    def __init__(
        self,
        skill: str,
        condition: Optional[str] = None,
        skill_args: str = "",
        skip_message: str = "Condition not met - skipped",
        timeout: int = 300
    ):
        """Initialize conditional skill SDK action.

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
        """Build the prompt to send to Claude SDK."""
        skill_invocation = f"/{self.skill}"
        if self.skill_args:
            skill_invocation += f" {self.skill_args}"

        if self.condition:
            return f"""First, evaluate this condition: {self.condition}

If the condition is TRUE: Run {skill_invocation}
If the condition is FALSE: Respond ONLY with: {self.skip_message}"""
        else:
            return skill_invocation

    async def _execute_async(self, ctx: 'RepoContext') -> ActionResult:
        """Execute skill via SDK asynchronously."""
        if not SDK_AVAILABLE:
            logger.error("claude-agent-sdk not installed")
            return ActionResult(
                status=Status.FAILED,
                message="claude-agent-sdk not installed - run: pip install claude-agent-sdk",
                action_name=self.name
            )

        prompt = self._build_prompt()
        prompt_preview = prompt[:100] + '...' if len(prompt) > 100 else prompt
        logger.info(f"Running skill /{self.skill} via SDK for {ctx.repo_name} | timeout: {self.timeout}s")
        logger.debug(f"Skill prompt: {prompt_preview} | cwd: {ctx.repo_path}")
        start_time = time.time()

        try:
            options = ClaudeAgentOptions(
                cwd=ctx.repo_path,
                permission_mode="acceptEdits"
            )

            async def consume_query():
                """Consume async iterator and return result."""
                async for message in query(prompt=prompt, options=options):
                    if hasattr(message, 'result'):
                        return message.result, getattr(message, 'total_cost_usd', None)
                return None, None

            # query() returns an AsyncIterator[Message], must iterate to get results
            result_text, cost_usd = await asyncio.wait_for(consume_query(), timeout=self.timeout)

            duration = time.time() - start_time

            # Check if the response indicates a skip
            if self.condition and self.skip_message in (result_text or ''):
                logger.debug(f"Skill /{self.skill} skipped for {ctx.repo_name} | condition not met | duration: {duration:.1f}s")
                return ActionResult(
                    status=Status.SKIPPED,
                    message=f"Skipped: {self.skip_message}",
                    action_name=self.name,
                    metadata={
                        'skill': self.skill,
                        'condition': self.condition,
                        'result': result_text
                    }
                )

            logger.debug(f"Skill /{self.skill} completed via SDK for {ctx.repo_name} | duration: {duration:.1f}s")
            return ActionResult(
                status=Status.SUCCESS,
                message=f"Skill /{self.skill} completed",
                action_name=self.name,
                metadata={
                    'skill': self.skill,
                    'result': result_text[:5000] if result_text else None,
                    'cost_usd': cost_usd,
                    'duration': duration
                }
            )

        except CLINotFoundError:
            logger.error(f"Claude CLI not found for {ctx.repo_name} | ensure 'claude' is installed and in PATH")
            return ActionResult(
                status=Status.FAILED,
                message="Claude CLI not found - ensure 'claude' is installed",
                action_name=self.name
            )
        except ProcessError as e:
            duration = time.time() - start_time
            logger.debug(f"Skill /{self.skill} failed for {ctx.repo_name} | duration: {duration:.1f}s | error: {e}")
            return ActionResult(
                status=Status.FAILED,
                message=f"Skill /{self.skill} failed: {e}",
                action_name=self.name,
                metadata={
                    'skill': self.skill,
                    'error': str(e),
                    'exit_code': getattr(e, 'exit_code', None)
                }
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Skill /{self.skill} timed out after {self.timeout}s for {ctx.repo_name} | "
                f"prompt: {prompt_preview} | cwd: {ctx.repo_path}"
            )
            return ActionResult(
                status=Status.FAILED,
                message=f"Skill /{self.skill} timed out after {self.timeout}s",
                action_name=self.name,
                metadata={'skill': self.skill, 'timeout': self.timeout, 'repo': ctx.repo_name}
            )
        except Exception as e:
            logger.error(f"Skill /{self.skill} error for {ctx.repo_name} | error: {e}", exc_info=True)
            return ActionResult(
                status=Status.FAILED,
                message=f"Skill error: {e}",
                action_name=self.name,
                metadata={'skill': self.skill, 'error': str(e)}
            )

    def execute(self, ctx: 'RepoContext') -> ActionResult:
        """Execute the skill via Claude SDK."""
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

        # Run async code from sync context with timeout
        try:
            return run_async_with_timeout(
                self._execute_async(ctx),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            prompt_preview = prompt[:100] + '...' if len(prompt) > 100 else prompt
            logger.error(
                f"Skill /{self.skill} timed out after {self.timeout}s for {ctx.repo_name} | "
                f"prompt: {prompt_preview} | cwd: {ctx.repo_path}"
            )
            return ActionResult(
                status=Status.FAILED,
                message=f"Skill /{self.skill} timed out after {self.timeout}s",
                action_name=self.name,
                metadata={'skill': self.skill, 'timeout': self.timeout, 'repo': ctx.repo_name}
            )

    def dry_run_message(self, ctx: 'RepoContext') -> str:
        skill_invocation = f"/{self.skill}"
        if self.skill_args:
            skill_invocation += f" {self.skill_args}"
        if self.condition:
            return f"Would run Claude SDK with skill: {skill_invocation} (condition: {self.condition[:50]}...)"
        return f"Would run Claude SDK with skill: {skill_invocation}"
