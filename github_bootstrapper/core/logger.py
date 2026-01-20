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

    logger = logging.getLogger('github_bootstrapper')
    logger.info(f"Starting GitHub {operation} operation")
    logger.info(f"Log file: {log_file}")

    return logger


def get_logger() -> logging.Logger:
    """Get the application logger.

    Returns:
        Logger instance
    """
    return logging.getLogger('github_bootstrapper')
