"""Settings-related pipelines (sandbox-enable, settings-clean)."""

from .base import Pipeline
from ..predicates import RepoExists
from ..actions.json_ops import JsonPatchAction
from ..actions.subprocess_ops import SubprocessAction


class SandboxEnablePipeline(Pipeline):
    """Enable Claude Code sandbox mode in repositories.

    This replaces SandboxEnableOperation with a pipeline-based implementation.
    """

    name = "sandbox-enable"
    description = "Enable Claude Code sandbox mode with auto-allow bash"
    requires_token = False
    safe_parallel = True

    def __init__(self):
        """Initialize sandbox-enable pipeline."""
        super().__init__()

        # Only run if repo exists
        self.when(RepoExists())

        # Patch the settings file
        self.then(JsonPatchAction(
            path=".claude/settings.local.json",
            patch={
                "sandbox": {
                    "enabled": True,
                    "autoAllowBashIfSandboxed": True
                }
            },
            create_if_missing=True
        ))


class SettingsCleanPipeline(Pipeline):
    """Clean Claude Code settings via settings-cleaner script.

    This replaces SettingsCleanOperation with a pipeline-based implementation.
    """

    name = "settings-clean"
    description = "Analyze and clean Claude Code settings"
    requires_token = False
    safe_parallel = True

    def __init__(self, mode: str = "analyze"):
        """Initialize settings-clean pipeline.

        Args:
            mode: Cleaning mode - 'analyze', 'clean', or 'auto-fix'
        """
        super().__init__()
        self.mode = mode

        # Only run if repo exists
        self.when(RepoExists())

        # Run the settings cleaner script
        # Note: This assumes uv and the script are available
        self.then(SubprocessAction(
            command=[
                "uv", "run",
                "python", "-m", "settings_cleaner",
                f"--mode={mode}"
            ],
            timeout=60
        ))


# Factory functions
def create_sandbox_enable_pipeline() -> SandboxEnablePipeline:
    """Create a sandbox-enable pipeline."""
    return SandboxEnablePipeline()


def create_settings_clean_pipeline(mode: str = "analyze") -> SettingsCleanPipeline:
    """Create a settings-clean pipeline.

    Args:
        mode: Cleaning mode

    Returns:
        Configured pipeline
    """
    return SettingsCleanPipeline(mode=mode)
