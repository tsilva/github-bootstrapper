"""Actions package for single-responsibility execution units."""

from .base import Action

from .git import (
    CloneAction,
    PullAction,
    FetchAction,
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
    # JSON actions
    'JsonPatchAction',
    'JsonReadAction',
    'deep_merge',
    # Subprocess actions
    'SubprocessAction',
    'ClaudeCliAction',
    'GhCliAction',
    # Description sync
    'DescriptionSyncAction',
    'extract_tagline',
    'truncate_description',
]
