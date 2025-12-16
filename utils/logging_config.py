"""
Logging configuration for the AI Activity Planner.

Provides structured logging with appropriate levels for production use.
"""
import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured logger instance.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Get root logger
    logger = logging.getLogger("app")
    logger.setLevel(log_level)
    logger.addHandler(console_handler)

    # Prevent duplicate logs
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name for the logger.

    Returns:
        Logger instance.
    """
    if name:
        return logging.getLogger(f"app.{name}")
    return logging.getLogger("app")
