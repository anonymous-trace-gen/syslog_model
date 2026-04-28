# Loguru configuration for agent activity logging.
from __future__ import annotations

import sys

from loguru import logger


def configure_logging(
    *,
    verbose: bool = False,
    quiet: bool = False,
    log_file: str | None = None,
) -> None:
    """Set up loguru sinks based on CLI flags.

    Args:
        verbose: Enable DEBUG level output.
        quiet: Suppress INFO, show only WARNING and above.
        log_file: Optional file path for persistent log output.
    """
    logger.remove()

    if quiet:
        level = "WARNING"
    elif verbose:
        level = "DEBUG"
    else:
        level = "INFO"

    logger.add(
        sys.stderr,
        level=level,
        format="<level>{level: <8}</level> | {message}",
        colorize=True,
    )

    if log_file:
        logger.add(
            log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            rotation="10 MB",
        )
