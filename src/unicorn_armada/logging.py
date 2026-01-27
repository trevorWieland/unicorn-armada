"""Structured JSONL logging.

This module provides a structured logging system using Pydantic models
for type-safe, machine-readable log entries. All log output is in JSONL
format (one JSON object per line).

Log format follows the standard: {timestamp, level, event, run_id, phase, message, data}
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import Literal, TextIO

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """Single log line in JSONL format."""

    timestamp: str = Field(..., description="ISO-8601 timestamp")
    level: Literal["debug", "info", "warn", "error"] = Field(
        ..., description="Log level"
    )
    event: str = Field(
        ..., description="Event type (e.g., run_started, phase_completed)"
    )
    run_id: str = Field(..., description="Pipeline run identifier")
    phase: str | None = Field(None, description="Pipeline phase if applicable")
    message: str = Field(..., description="Human-readable log message")
    data: dict[str, str | int | float | bool | None] | None = Field(
        None, description="Structured event data"
    )


class Logger:
    """Structured JSONL logger.

    Outputs log entries as JSONL to the specified stream (stderr by default).
    Each log entry is a single line of JSON.

    Usage:
        logger = Logger(run_id="abc123")
        logger.info("run_started", "Starting pipeline run")
        logger.info(
            "phase_completed", "Translation complete",
            phase="translate", data={"scenes": 10}
        )
        logger.error("error_occurred", "Failed to connect", data={"error": "timeout"})
    """

    def __init__(
        self,
        run_id: str,
        stream: TextIO | None = None,
        min_level: Literal["debug", "info", "warn", "error"] = "info",
    ) -> None:
        """Initialize logger.

        Args:
            run_id: Identifier for the current run/session.
            stream: Output stream (defaults to stderr).
            min_level: Minimum log level to output.
        """
        self.run_id = run_id
        self.stream = stream or sys.stderr
        self.min_level = min_level
        self._level_order = {"debug": 0, "info": 1, "warn": 2, "error": 3}

    def _should_log(self, level: Literal["debug", "info", "warn", "error"]) -> bool:
        """Check if the given level should be logged."""
        return self._level_order[level] >= self._level_order[self.min_level]

    def _emit(
        self,
        level: Literal["debug", "info", "warn", "error"],
        event: str,
        message: str,
        phase: str | None = None,
        data: dict[str, str | int | float | bool | None] | None = None,
    ) -> None:
        """Emit a log entry."""
        if not self._should_log(level):
            return

        entry = LogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            level=level,
            event=event,
            run_id=self.run_id,
            phase=phase,
            message=message,
            data=data,
        )
        self.stream.write(entry.model_dump_json() + "\n")
        self.stream.flush()

    def debug(
        self,
        event: str,
        message: str,
        *,
        phase: str | None = None,
        data: dict[str, str | int | float | bool | None] | None = None,
    ) -> None:
        """Log a debug message."""
        self._emit("debug", event, message, phase, data)

    def info(
        self,
        event: str,
        message: str,
        *,
        phase: str | None = None,
        data: dict[str, str | int | float | bool | None] | None = None,
    ) -> None:
        """Log an info message."""
        self._emit("info", event, message, phase, data)

    def warn(
        self,
        event: str,
        message: str,
        *,
        phase: str | None = None,
        data: dict[str, str | int | float | bool | None] | None = None,
    ) -> None:
        """Log a warning message."""
        self._emit("warn", event, message, phase, data)

    def error(
        self,
        event: str,
        message: str,
        *,
        phase: str | None = None,
        data: dict[str, str | int | float | bool | None] | None = None,
    ) -> None:
        """Log an error message."""
        self._emit("error", event, message, phase, data)


# Standard event names
class Events:
    """Standard event names for logging."""

    # Lifecycle events
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"

    # Phase events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"

    # Data events
    DATA_LOADED = "data_loaded"
    DATA_VALIDATED = "data_validated"
    DATA_WRITTEN = "data_written"

    # Solver events
    SOLVE_STARTED = "solve_started"
    SOLVE_COMPLETED = "solve_completed"
    SOLVE_FAILED = "solve_failed"

    # Error events
    ERROR_OCCURRED = "error_occurred"
    VALIDATION_FAILED = "validation_failed"
