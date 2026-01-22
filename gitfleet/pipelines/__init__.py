"""Pipelines package for composable repository operations."""

from .base import Pipeline, PipelineStep, Branch, PipelineBuilder

from .executor import PipelineExecutor, action_result_to_operation_result

from .registry import PipelineRegistry, pipeline_registry

from .adapter import PipelineAsOperation, pipeline_to_operation_class

from .git_ops import (
    SyncPipeline,
    CloneOnlyPipeline,
    PullOnlyPipeline,
    create_sync_pipeline,
    create_clone_only_pipeline,
    create_pull_only_pipeline,
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
    # Adapter
    'PipelineAsOperation',
    'pipeline_to_operation_class',
    # Git pipelines
    'SyncPipeline',
    'CloneOnlyPipeline',
    'PullOnlyPipeline',
    'create_sync_pipeline',
    'create_clone_only_pipeline',
    'create_pull_only_pipeline',
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
]
