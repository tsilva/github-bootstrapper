"""MCP-specific logging utilities.

Provides logging configuration and helper functions for MCP tools.
"""

import os
import sys
import time
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any, Generator


# Unicode symbols for log output
CHECK = "\u2713"  # checkmark
CROSS = "\u2717"  # x mark
SKIP = "\u2298"   # circled division slash


def setup_mcp_logging(operation: str = "server") -> logging.Logger:
    """Configure logging for MCP operations.

    Creates a logger that writes DEBUG to file and INFO to console.

    Args:
        operation: Name of the operation for log filename

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Create timestamp-based log filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(logs_dir, f'mcp_{operation}_{timestamp}.log')

    # Get or create the MCP logger
    logger = logging.getLogger('gitfleet.mcp')

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    # File handler - DEBUG level
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)

    # Console handler - INFO level
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    logger.info(f"MCP logging initialized: {log_file}")

    return logger


def get_mcp_logger() -> logging.Logger:
    """Get the MCP logger instance.

    Returns:
        Logger instance for gitfleet.mcp
    """
    return logging.getLogger('gitfleet.mcp')


@contextmanager
def timed_operation(
    name: str,
    logger: Optional[logging.Logger] = None,
    **context: Any
) -> Generator[Dict[str, Any], None, None]:
    """Context manager for timing operations.

    Usage:
        with timed_operation("list_repos", logger, count=10) as timing:
            # do work
        print(f"Took {timing['duration_ms']}ms")

    Args:
        name: Name of the operation being timed
        logger: Optional logger instance (uses MCP logger if not provided)
        **context: Additional context to log

    Yields:
        Dict containing timing info (updated with duration after completion)
    """
    log = logger or get_mcp_logger()
    timing_info: Dict[str, Any] = {
        'name': name,
        'start_time': time.time(),
        'duration_ms': 0,
        **context
    }

    context_str = ', '.join(f'{k}={v}' for k, v in context.items()) if context else ''
    if context_str:
        log.debug(f"Starting {name}: {context_str}")
    else:
        log.debug(f"Starting {name}")

    try:
        yield timing_info
    finally:
        end_time = time.time()
        timing_info['duration_ms'] = int((end_time - timing_info['start_time']) * 1000)
        log.debug(f"Completed {name} in {timing_info['duration_ms']}ms")


def log_repo_result(
    repo: str,
    status: str,
    message: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """Log a per-repository result with consistent formatting.

    Args:
        repo: Repository name
        status: Result status ("success", "failed", "skipped")
        message: Optional message to include
        logger: Optional logger instance
    """
    log = logger or get_mcp_logger()

    if status == "success":
        symbol = CHECK
        level = logging.INFO
    elif status == "failed":
        symbol = CROSS
        level = logging.WARNING
    elif status == "skipped":
        symbol = SKIP
        level = logging.INFO
    else:
        symbol = "?"
        level = logging.INFO

    msg = f"{symbol} {repo}"
    if message:
        msg += f": {message}"

    log.log(level, msg)


def log_summary(
    tool_name: str,
    total: int,
    success: int,
    failed: int,
    skipped: int,
    duration_ms: int,
    logger: Optional[logging.Logger] = None
) -> None:
    """Log a summary block for a tool execution.

    Args:
        tool_name: Name of the tool that was executed
        total: Total number of items processed
        success: Number of successful items
        failed: Number of failed items
        skipped: Number of skipped items
        duration_ms: Duration in milliseconds
        logger: Optional logger instance
    """
    log = logger or get_mcp_logger()

    duration_s = duration_ms / 1000
    separator = "=" * 50

    log.info(separator)
    log.info(f"Summary: {tool_name}")
    log.info(f"Total: {total}, Success: {success}, Failed: {failed}, Skipped: {skipped}")
    log.info(f"Duration: {duration_ms}ms ({duration_s:.2f}s)")
    log.info(separator)


def log_tool_invocation(
    tool_name: str,
    arguments: Dict[str, Any],
    logger: Optional[logging.Logger] = None
) -> None:
    """Log a tool invocation with arguments.

    Args:
        tool_name: Name of the tool being invoked
        arguments: Tool arguments
        logger: Optional logger instance
    """
    log = logger or get_mcp_logger()
    log.info(f"Tool invoked: {tool_name}")
    log.debug(f"Arguments: {arguments}")


# ============================================================================
# Claude execution logging
# ============================================================================

def log_claude_session_start(
    session_id: str,
    repos: list,
    command: str,
    parallel: bool,
    workers: int,
    logger: Optional[logging.Logger] = None
) -> None:
    """Log start of Claude execution session.

    Args:
        session_id: Unique session identifier
        repos: List of repository names
        command: The Claude command being executed
        parallel: Whether execution is parallel
        workers: Number of parallel workers
        logger: Optional logger instance
    """
    log = logger or get_mcp_logger()
    log.info(f"[claude-exec] Session {session_id}: {len(repos)} repos, parallel={parallel}, workers={workers}")
    cmd_preview = command[:100] + '...' if len(command) > 100 else command
    log.info(f"[claude-exec] Command: {cmd_preview}")


def log_claude_worker_start(
    session_id: str,
    worker_id: int,
    repo: str,
    prompt_preview: str,
    logger: Optional[logging.Logger] = None
) -> None:
    """Log Claude worker starting execution.

    Args:
        session_id: Session identifier
        worker_id: Worker thread identifier
        repo: Repository name
        prompt_preview: Truncated prompt for logging
        logger: Optional logger instance
    """
    log = logger or get_mcp_logger()
    log.info(f"[{session_id}][worker-{worker_id}] {repo}: Starting")
    log.debug(f"[{session_id}][worker-{worker_id}] {repo}: prompt={prompt_preview}")


def log_claude_worker_complete(
    session_id: str,
    worker_id: int,
    repo: str,
    success: bool,
    output_chars: int,
    duration_s: float,
    log_path: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """Log Claude worker completion.

    Args:
        session_id: Session identifier
        worker_id: Worker thread identifier
        repo: Repository name
        success: Whether execution succeeded
        output_chars: Number of characters in output
        duration_s: Execution duration in seconds
        log_path: Path to per-repo log file
        logger: Optional logger instance
    """
    log = logger or get_mcp_logger()
    status = "Completed" if success else "Failed"
    log.info(f"[{session_id}][worker-{worker_id}] {repo}: {status} in {duration_s:.1f}s ({output_chars} chars)")
    if log_path:
        log.debug(f"[{session_id}][worker-{worker_id}] {repo}: Output logged to {log_path}")


def log_claude_session_complete(
    session_id: str,
    output_dir: str,
    logger: Optional[logging.Logger] = None
) -> None:
    """Log end of Claude execution session.

    Args:
        session_id: Session identifier
        output_dir: Directory containing per-repo logs
        logger: Optional logger instance
    """
    log = logger or get_mcp_logger()
    log.info(f"[claude-exec] Session {session_id} complete. Logs: {output_dir}")
