"""Pipeline class with fluent API for composing operations."""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Union, Tuple, TYPE_CHECKING

from ..predicates.base import Predicate, AllOf, AlwaysTrue
from ..actions.base import Action
from ..core.types import RepoContext, ActionResult, Status

if TYPE_CHECKING:
    pass

logger = logging.getLogger('gitfleet')


@dataclass
class PipelineStep:
    """A single step in a pipeline."""
    action: Action
    predicate: Optional[Predicate] = None  # None means always run
    stop_on_failure: bool = True  # Stop pipeline if this step fails


@dataclass
class Branch:
    """A conditional branch in a pipeline."""
    predicate: Predicate
    action: Action
    else_action: Optional[Action] = None


class Pipeline:
    """Composable pipeline for repository operations.

    Pipelines allow you to define a sequence of actions with predicates,
    creating reusable and composable operation definitions.

    Example usage:
        # Simple linear pipeline
        pipeline = Pipeline("my-pipeline").when(
            RepoExists()
        ).then(
            PullAction()
        )

        # Pipeline with branching
        sync_pipeline = Pipeline("sync").branch(
            when=not_(RepoExists()),
            then=CloneAction()
        ).branch(
            when=all_of(RepoExists(), RepoClean()),
            then=PullAction()
        )
    """

    # Class attributes for registry
    name: str = "base"
    description: str = "Base pipeline"
    requires_token: bool = False
    safe_parallel: bool = True
    show_progress_only: bool = False
    default_workers: Optional[int] = None

    def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
        """Initialize a pipeline.

        Args:
            name: Pipeline name (overrides class attribute)
            description: Pipeline description (overrides class attribute)
        """
        if name:
            self.name = name
        if description:
            self.description = description

        self._predicates: List[Predicate] = []
        self._steps: List[PipelineStep] = []
        self._branches: List[Branch] = []

    def when(self, *predicates: Predicate) -> 'Pipeline':
        """Add predicates that must pass before pipeline executes.

        All predicates are combined with AND logic.

        Args:
            *predicates: Predicates to add

        Returns:
            Self for chaining
        """
        self._predicates.extend(predicates)
        return self

    def then(self, action: Action, stop_on_failure: bool = True) -> 'Pipeline':
        """Add an action to execute unconditionally.

        Args:
            action: Action to execute
            stop_on_failure: Stop pipeline if action fails

        Returns:
            Self for chaining
        """
        self._steps.append(PipelineStep(
            action=action,
            predicate=None,
            stop_on_failure=stop_on_failure
        ))
        return self

    def then_if(
        self,
        predicate: Predicate,
        action: Action,
        stop_on_failure: bool = True
    ) -> 'Pipeline':
        """Add an action that only executes if predicate passes.

        Args:
            predicate: Predicate to check
            action: Action to execute if predicate passes
            stop_on_failure: Stop pipeline if action fails

        Returns:
            Self for chaining
        """
        self._steps.append(PipelineStep(
            action=action,
            predicate=predicate,
            stop_on_failure=stop_on_failure
        ))
        return self

    def branch(
        self,
        when: Predicate,
        then: Action,
        else_: Optional[Action] = None
    ) -> 'Pipeline':
        """Add a conditional branch.

        If predicate passes, execute 'then' action.
        Optionally execute 'else_' action if predicate fails.

        Args:
            when: Predicate to check
            then: Action if predicate passes
            else_: Optional action if predicate fails

        Returns:
            Self for chaining
        """
        self._branches.append(Branch(
            predicate=when,
            action=then,
            else_action=else_
        ))
        return self

    def should_skip(self, ctx: RepoContext) -> Optional[str]:
        """Check if pipeline should skip this repository.

        Args:
            ctx: Repository context

        Returns:
            Skip reason if should skip, None otherwise
        """
        if not self._predicates:
            return None

        combined = AllOf(*self._predicates) if len(self._predicates) > 1 else self._predicates[0]
        passes, reason = combined.check(ctx)

        if not passes:
            return reason
        return None

    def execute(self, ctx: RepoContext) -> ActionResult:
        """Execute the pipeline on a repository.

        Args:
            ctx: Repository context

        Returns:
            Final ActionResult from pipeline execution
        """
        # Check global predicates
        skip_reason = self.should_skip(ctx)
        if skip_reason:
            return ActionResult(
                status=Status.SKIPPED,
                message=skip_reason,
                action_name=self.name
            )

        # Execute branches first (they're typically conditional paths)
        for branch in self._branches:
            passes, reason = branch.predicate.check(ctx)
            if passes:
                result = branch.action.execute(ctx)
                ctx.add_result(result)
                if result.failed:
                    return result
                # Branch matched and executed, continue to next branch
            elif branch.else_action:
                result = branch.else_action.execute(ctx)
                ctx.add_result(result)
                if result.failed:
                    return result

        # Execute linear steps
        for step in self._steps:
            # Check step predicate if present
            if step.predicate:
                passes, reason = step.predicate.check(ctx)
                if not passes:
                    # Skip this step
                    ctx.add_result(ActionResult(
                        status=Status.SKIPPED,
                        message=reason,
                        action_name=step.action.name
                    ))
                    continue

            # Execute action
            result = step.action.execute(ctx)
            ctx.add_result(result)

            # Check for failure
            if result.failed and step.stop_on_failure:
                return result

        # Return last result or success if no steps
        if ctx.results:
            return ctx.last_result
        else:
            return ActionResult(
                status=Status.SUCCESS,
                message="Pipeline completed (no actions)",
                action_name=self.name
            )

    def get_description(self) -> str:
        """Get a description of this pipeline's behavior."""
        parts = [f"Pipeline: {self.name}"]
        if self.description:
            parts.append(f"  {self.description}")
        if self._predicates:
            parts.append(f"  Conditions: {len(self._predicates)} predicate(s)")
        if self._branches:
            parts.append(f"  Branches: {len(self._branches)}")
        if self._steps:
            parts.append(f"  Steps: {len(self._steps)}")
        return "\n".join(parts)


class PipelineBuilder:
    """Factory for creating common pipeline patterns."""

    @staticmethod
    def linear(name: str, *actions: Action, predicates: List[Predicate] = None) -> Pipeline:
        """Create a linear pipeline that executes actions in sequence.

        Args:
            name: Pipeline name
            *actions: Actions to execute in order
            predicates: Optional predicates that must pass

        Returns:
            Configured Pipeline
        """
        pipeline = Pipeline(name)
        if predicates:
            pipeline.when(*predicates)
        for action in actions:
            pipeline.then(action)
        return pipeline

    @staticmethod
    def conditional(
        name: str,
        branches: List[Tuple[Predicate, Action]]
    ) -> Pipeline:
        """Create a pipeline with conditional branches.

        Args:
            name: Pipeline name
            branches: List of (predicate, action) tuples

        Returns:
            Configured Pipeline
        """
        pipeline = Pipeline(name)
        for pred, action in branches:
            pipeline.branch(when=pred, then=action)
        return pipeline
