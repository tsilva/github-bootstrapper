"""Logging configuration and utilities."""

import os
import sys
import logging
from datetime import datetime
from typing import Optional


def setup_logging(operation: str = "sync") -> logging.Logger:
    """Configure logging to both file and console.

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
    log_file = os.path.join(logs_dir, f'github_{operation}_{timestamp}.log')

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Reset any existing configuration
    )

    logger = logging.getLogger('gitfleet')
    logger.info(f"Starting GitHub {operation} operation")
    logger.info(f"Log file: {log_file}")

    return logger


def get_logger() -> logging.Logger:
    """Get the application logger.

    Returns:
        Logger instance
    """
    return logging.getLogger('gitfleet')


def write_claude_output_log(
    session_id: str,
    repo_name: str,
    prompt: str,
    output: str,
    duration_s: float,
    cost_usd: Optional[float] = None,
    error: Optional[str] = None,
    cwd: Optional[str] = None
) -> str:
    """Write full Claude output to per-repo log file.

    Args:
        session_id: Session identifier for grouping logs
        repo_name: Name of the repository
        prompt: The prompt that was executed
        output: Full output from Claude
        duration_s: Execution duration in seconds
        cost_usd: Optional cost in USD
        error: Optional error message if failed
        cwd: Optional working directory

    Returns:
        Path to the created log file
    """
    from pathlib import Path

    output_dir = Path(os.getcwd()) / "logs" / "claude_outputs" / session_id
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"{repo_name}.log"

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status = "Success" if not error else f"Failed: {error}"
    cost_str = f"${cost_usd:.4f}" if cost_usd else "N/A"

    content = f"""{'='*80}
Claude Execution Log
{'='*80}
Repository: {repo_name}
Prompt: {prompt[:200]}{'...' if len(prompt) > 200 else ''}
Started: {timestamp}
Working Directory: {cwd or 'N/A'}
{'-'*80}

{output or '(no output)'}

{'-'*80}
Duration: {duration_s:.1f}s
Cost: {cost_str}
Status: {status}
{'='*80}
"""
    log_path.write_text(content)
    return str(log_path)
