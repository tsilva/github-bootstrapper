"""Base classes and combinators for predicates."""

from abc import ABC, abstractmethod
from typing import Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.types import RepoContext


class Predicate(ABC):
    """Base class for predicates that determine if an action should run.

    Predicates are composable conditions that can be combined using
    combinators like all_of(), any_of(), and not_().
    """

    @abstractmethod
    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        """Check if the predicate passes.

        Args:
            ctx: Repository context

        Returns:
            (passes, reason) - bool indicating if predicate passes and explanation
        """
        pass

    def __and__(self, other: 'Predicate') -> 'AllOf':
        """Combine predicates with AND logic."""
        return AllOf(self, other)

    def __or__(self, other: 'Predicate') -> 'AnyOf':
        """Combine predicates with OR logic."""
        return AnyOf(self, other)

    def __invert__(self) -> 'Not':
        """Negate a predicate."""
        return Not(self)


class AllOf(Predicate):
    """Combinator: all predicates must pass (AND logic)."""

    def __init__(self, *predicates: Predicate):
        """Initialize with predicates.

        Args:
            *predicates: Predicates that must all pass
        """
        self.predicates: List[Predicate] = []
        for p in predicates:
            # Flatten nested AllOf
            if isinstance(p, AllOf):
                self.predicates.extend(p.predicates)
            else:
                self.predicates.append(p)

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        """Check if all predicates pass."""
        for predicate in self.predicates:
            passes, reason = predicate.check(ctx)
            if not passes:
                return False, reason
        return True, "All conditions met"


class AnyOf(Predicate):
    """Combinator: at least one predicate must pass (OR logic)."""

    def __init__(self, *predicates: Predicate):
        """Initialize with predicates.

        Args:
            *predicates: Predicates where at least one must pass
        """
        self.predicates: List[Predicate] = []
        for p in predicates:
            # Flatten nested AnyOf
            if isinstance(p, AnyOf):
                self.predicates.extend(p.predicates)
            else:
                self.predicates.append(p)

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        """Check if any predicate passes."""
        reasons = []
        for predicate in self.predicates:
            passes, reason = predicate.check(ctx)
            if passes:
                return True, reason
            reasons.append(reason)
        return False, "; ".join(reasons)


class Not(Predicate):
    """Combinator: negate a predicate."""

    def __init__(self, predicate: Predicate):
        """Initialize with predicate to negate.

        Args:
            predicate: Predicate to negate
        """
        self.predicate = predicate

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        """Check if predicate fails (negation)."""
        passes, reason = self.predicate.check(ctx)
        if passes:
            return False, f"Not: {reason}"
        return True, f"Not: {reason}"


# Convenience functions for creating combinators
def all_of(*predicates: Predicate) -> AllOf:
    """Create an AllOf combinator from predicates."""
    return AllOf(*predicates)


def any_of(*predicates: Predicate) -> AnyOf:
    """Create an AnyOf combinator from predicates."""
    return AnyOf(*predicates)


def not_(predicate: Predicate) -> Not:
    """Create a Not combinator from a predicate."""
    return Not(predicate)


class AlwaysTrue(Predicate):
    """Predicate that always passes."""

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        return True, "Always passes"


class AlwaysFalse(Predicate):
    """Predicate that always fails."""

    def __init__(self, reason: str = "Always fails"):
        self.reason = reason

    def check(self, ctx: 'RepoContext') -> Tuple[bool, str]:
        return False, self.reason
