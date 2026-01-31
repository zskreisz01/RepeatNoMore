"""Structured logging configuration for RepeatNoMore."""

import logging
import sys
from typing import Any, Dict
from datetime import datetime

import structlog
from app.config import get_settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer() if settings.is_development
            else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        structlog.BoundLogger: Configured logger
    """
    return structlog.get_logger(name)


class RequestLogger:
    """Context manager for logging requests with timing."""

    def __init__(self, logger: structlog.BoundLogger, operation: str, **kwargs):
        """
        Initialize request logger.

        Args:
            logger: Logger instance
            operation: Operation description
            **kwargs: Additional context to log
        """
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None

    def __enter__(self):
        """Start logging context."""
        self.start_time = datetime.now()
        self.logger.info(
            f"{self.operation} started",
            **self.context
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End logging context with duration."""
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is not None:
            self.logger.error(
                f"{self.operation} failed",
                duration_seconds=duration,
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context
            )
        else:
            self.logger.info(
                f"{self.operation} completed",
                duration_seconds=duration,
                **self.context
            )

        return False  # Don't suppress exceptions
