"""Skill-based pipelines for invoking Claude skills across repositories."""

from typing import Optional

from .base import Pipeline
from ..predicates import RepoExists
from ..actions.subprocess_ops import ConditionalSkillAction


class ReadmeGeneratorPipeline(Pipeline):
    """Generate README files using readme-generator skill."""

    name = "readme-generator"
    description = "Generate README.md using readme-generator skill"
    requires_token = False
    safe_parallel = False  # Sequential for Claude API rate limits

    def __init__(self, condition: Optional[str] = None):
        """Initialize readme-generator pipeline.

        Args:
            condition: Optional condition for Claude to evaluate before running.
                       If None, skill runs unconditionally.
        """
        super().__init__()
        self.condition = condition

        self.when(RepoExists())
        self.then(ConditionalSkillAction(
            skill="readme-generator",
            condition=condition,
            skip_message="Skipped - condition not met",
            timeout=300
        ))


class LogoGeneratorPipeline(Pipeline):
    """Generate repo logos using repo-logo-generator skill."""

    name = "logo-generator"
    description = "Generate repository logo using repo-logo-generator skill"
    requires_token = False
    safe_parallel = False  # Sequential for Claude API rate limits

    def __init__(self, condition: Optional[str] = None):
        """Initialize logo-generator pipeline.

        Args:
            condition: Optional condition for Claude to evaluate before running.
                       If None, skill runs unconditionally.
        """
        super().__init__()
        self.condition = condition

        self.when(RepoExists())
        self.then(ConditionalSkillAction(
            skill="repo-logo-generator",
            condition=condition,
            skip_message="Skipped - condition not met",
            timeout=300
        ))


class SettingsOptimizerPipeline(Pipeline):
    """Optimize Claude settings using claude-settings-optimizer skill."""

    name = "settings-optimizer"
    description = "Optimize Claude Code settings using claude-settings-optimizer skill"
    requires_token = False
    safe_parallel = False  # Sequential for Claude API rate limits

    def __init__(self, mode: str = "analyze"):
        """Initialize settings-optimizer pipeline.

        Args:
            mode: Operation mode - 'analyze', 'clean', or 'auto-fix'
        """
        super().__init__()
        self.mode = mode

        self.when(RepoExists())
        self.then(ConditionalSkillAction(
            skill="claude-settings-optimizer",
            skill_args=f"--mode {mode}",
            timeout=120
        ))


class RepoNameGeneratorPipeline(Pipeline):
    """Generate repository names using repo-name-generator skill."""

    name = "name-generator"
    description = "Generate repository name suggestions using repo-name-generator skill"
    requires_token = False
    safe_parallel = False  # Sequential for Claude API rate limits

    def __init__(self, condition: Optional[str] = None):
        """Initialize name-generator pipeline.

        Args:
            condition: Optional condition for Claude to evaluate before running.
                       If None, skill runs unconditionally.
        """
        super().__init__()
        self.condition = condition

        self.when(RepoExists())
        self.then(ConditionalSkillAction(
            skill="repo-name-generator",
            condition=condition,
            skip_message="Skipped - condition not met",
            timeout=120
        ))


# Factory functions
def create_readme_generator_pipeline(
    condition: Optional[str] = None
) -> ReadmeGeneratorPipeline:
    """Create a readme-generator pipeline.

    Args:
        condition: Optional condition for Claude to evaluate

    Returns:
        Configured pipeline
    """
    return ReadmeGeneratorPipeline(condition=condition)


def create_logo_generator_pipeline(
    condition: Optional[str] = None
) -> LogoGeneratorPipeline:
    """Create a logo-generator pipeline.

    Args:
        condition: Optional condition for Claude to evaluate

    Returns:
        Configured pipeline
    """
    return LogoGeneratorPipeline(condition=condition)


def create_settings_optimizer_pipeline(
    mode: str = "analyze"
) -> SettingsOptimizerPipeline:
    """Create a settings-optimizer pipeline.

    Args:
        mode: Operation mode

    Returns:
        Configured pipeline
    """
    return SettingsOptimizerPipeline(mode=mode)


def create_name_generator_pipeline(
    condition: Optional[str] = None
) -> RepoNameGeneratorPipeline:
    """Create a name-generator pipeline.

    Args:
        condition: Optional condition for Claude to evaluate

    Returns:
        Configured pipeline
    """
    return RepoNameGeneratorPipeline(condition=condition)
