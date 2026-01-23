"""Async bridge utilities for running async code from sync contexts.

This module provides utilities to bridge the gap between the async-native
claude-agent-sdk and the sync-based ThreadPoolExecutor used in gitfleet.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar, Coroutine, Any, Optional

T = TypeVar('T')


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine from a synchronous context.

    This function handles the common case where we need to call async SDK
    methods from synchronous code (e.g., from within a ThreadPoolExecutor).

    It creates a new event loop for each call to avoid issues with nested
    event loops or reusing closed loops.

    Args:
        coro: The coroutine to execute

    Returns:
        The result of the coroutine

    Raises:
        Any exception raised by the coroutine
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def run_async_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float
) -> T:
    """Run an async coroutine with a timeout.

    Args:
        coro: The coroutine to execute
        timeout: Timeout in seconds

    Returns:
        The result of the coroutine

    Raises:
        asyncio.TimeoutError: If the coroutine times out
        Any exception raised by the coroutine
    """
    async def with_timeout():
        return await asyncio.wait_for(coro, timeout=timeout)

    return run_async(with_timeout())


class AsyncBridge:
    """A context manager for efficient async execution from sync code.

    Use this when you need to run multiple async operations efficiently,
    as it reuses a single event loop.

    Example:
        with AsyncBridge() as bridge:
            result1 = bridge.run(async_func1())
            result2 = bridge.run(async_func2())
    """

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def __enter__(self) -> 'AsyncBridge':
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._loop:
            self._loop.close()
            asyncio.set_event_loop(None)
            self._loop = None
        return False

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run an async coroutine.

        Args:
            coro: The coroutine to execute

        Returns:
            The result of the coroutine
        """
        if not self._loop:
            raise RuntimeError("AsyncBridge not entered as context manager")
        return self._loop.run_until_complete(coro)

    def run_with_timeout(
        self,
        coro: Coroutine[Any, Any, T],
        timeout: float
    ) -> T:
        """Run an async coroutine with a timeout.

        Args:
            coro: The coroutine to execute
            timeout: Timeout in seconds

        Returns:
            The result of the coroutine

        Raises:
            asyncio.TimeoutError: If the coroutine times out
        """
        async def with_timeout():
            return await asyncio.wait_for(coro, timeout=timeout)

        return self.run(with_timeout())
