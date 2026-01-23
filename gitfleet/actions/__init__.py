"""Actions package for single-responsibility execution units."""

from .base import Action

from .git import (
    CloneAction,
    PullAction,
    FetchAction,
    GitAddAction,
    GitCommitAction,
    GitPushAction,
)

from .json_ops import (
    JsonPatchAction,
    JsonReadAction,
    deep_merge,
)

from .subprocess_ops import (
    SubprocessAction,
    ClaudeCliAction,
    GhCliAction,
    ClaudeCommitMessageAction,
    ConditionalSkillAction,
)

from .claude_sdk import (
    ClaudeSDKAction,
    ConditionalSkillSDKAction,
)

from .description_sync import (
    DescriptionSyncAction,
    extract_tagline,
    truncate_description,
)

__all__ = [
    # Base
    'Action',
    # Git actions
    'CloneAction',
    'PullAction',
    'FetchAction',
    'GitAddAction',
    'GitCommitAction',
    'GitPushAction',
    # JSON actions
    'JsonPatchAction',
    'JsonReadAction',
    'deep_merge',
    # Subprocess actions (legacy/fallback)
    'SubprocessAction',
    'ClaudeCliAction',
    'GhCliAction',
    'ClaudeCommitMessageAction',
    'ConditionalSkillAction',
    # Claude SDK actions (preferred)
    'ClaudeSDKAction',
    'ConditionalSkillSDKAction',
    # Description sync
    'DescriptionSyncAction',
    'extract_tagline',
    'truncate_description',
]
