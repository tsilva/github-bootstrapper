"""Pipelines package for composable repository operations."""

from .base import Pipeline, PipelineStep, Branch, PipelineBuilder

from .executor import PipelineExecutor, action_result_to_operation_result

from .registry import PipelineRegistry, pipeline_registry

from .git_ops import (
    SyncPipeline,
    CloneOnlyPipeline,
    PullOnlyPipeline,
    CommitPushPipeline,
    create_sync_pipeline,
    create_clone_only_pipeline,
    create_pull_only_pipeline,
    create_commit_push_pipeline,
)

from .settings_ops import (
    SandboxEnablePipeline,
    SettingsCleanPipeline,
    create_sandbox_enable_pipeline,
    create_settings_clean_pipeline,
)

from .subprocess_ops import (
    DescriptionSyncPipeline,
    ClaudePipeline,
    create_description_sync_pipeline,
    create_claude_pipeline,
)

from .status_ops import (
    StatusPipeline,
    StatusCheckAction,
)

__all__ = [
    # Base
    'Pipeline',
    'PipelineStep',
    'Branch',
    'PipelineBuilder',
    # Executor
    'PipelineExecutor',
    'action_result_to_operation_result',
    # Registry
    'PipelineRegistry',
    'pipeline_registry',
    # Git pipelines
    'SyncPipeline',
    'CloneOnlyPipeline',
    'PullOnlyPipeline',
    'CommitPushPipeline',
    'create_sync_pipeline',
    'create_clone_only_pipeline',
    'create_pull_only_pipeline',
    'create_commit_push_pipeline',
    # Settings pipelines
    'SandboxEnablePipeline',
    'SettingsCleanPipeline',
    'create_sandbox_enable_pipeline',
    'create_settings_clean_pipeline',
    # Subprocess pipelines
    'DescriptionSyncPipeline',
    'ClaudePipeline',
    'create_description_sync_pipeline',
    'create_claude_pipeline',
    # Status pipeline
    'StatusPipeline',
    'StatusCheckAction',
]
