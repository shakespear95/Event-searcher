"""
Structured logging configuration.
Logs every tool call for traceability (Rule A5).
"""
import io
import sys
from typing import Any

import structlog

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def configure_logging(log_level: str = "DEBUG", json_logs: bool = False) -> None:
    """Configure structured logging for the application."""

    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        # JSON format for production
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty format for development
        shared_processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with the given name."""
    return structlog.get_logger(name)


class ToolCallLogger:
    """
    Logger specifically for tool calls.
    Ensures every API/tool call is logged before execution (Rule A5).
    """

    def __init__(self, tool_name: str):
        self.logger = get_logger(f"tool.{tool_name}")
        self.tool_name = tool_name

    def log_call(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log a tool call before execution."""
        self.logger.info(
            f"TOOL_CALL: {self.tool_name}",
            action=action,
            params=params or {},
            **kwargs,
        )

    def log_result(
        self,
        action: str,
        success: bool,
        result: Any = None,
        error: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Log tool call result after execution."""
        if success:
            self.logger.info(
                f"TOOL_RESULT: {self.tool_name}",
                action=action,
                success=True,
                result_type=type(result).__name__ if result else None,
                **kwargs,
            )
        else:
            self.logger.error(
                f"TOOL_ERROR: {self.tool_name}",
                action=action,
                success=False,
                error=error,
                **kwargs,
            )

    def log_source(self, source_api: str, source_url: str, data_type: str) -> None:
        """Log data source for traceability (Rule A3)."""
        self.logger.info(
            "DATA_SOURCE",
            tool=self.tool_name,
            source_api=source_api,
            source_url=source_url,
            data_type=data_type,
        )
