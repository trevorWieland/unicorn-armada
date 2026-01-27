"""API response envelope models.

This module provides the standard API response envelope structure
used by all CLI JSON outputs. The envelope format ensures consistent
parsing for both success and error cases.

Standard format: {data, error, meta}
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class MetaInfo(BaseModel):
    """Metadata for API responses."""

    timestamp: str = Field(..., description="ISO-8601 timestamp")

    @classmethod
    def now(cls) -> MetaInfo:
        """Create MetaInfo with current timestamp."""
        return cls(timestamp=datetime.now(UTC).isoformat())


class ErrorDetails(BaseModel):
    """Detailed error context."""

    field: str | None = Field(None, description="Field name if validation error")
    provided: str | None = Field(None, description="Value that was provided")
    valid_options: list[str] | None = Field(
        None, description="Valid values if applicable"
    )


class ErrorResponse(BaseModel):
    """Error information in response."""

    code: str = Field(..., description="Error code (e.g., VAL_001, IO_001)")
    message: str = Field(..., description="Human-readable error message")
    details: ErrorDetails | None = Field(None, description="Additional error context")


class APIResponse[T](BaseModel):
    """Generic API response envelope.

    All CLI JSON responses use this envelope structure to ensure
    consistent parsing. Either data or error will be set, never both.

    Success example:
        {
            "data": {"run_id": "abc123", "status": "running"},
            "error": null,
            "meta": {"timestamp": "2026-01-23T12:00:00Z"}
        }

    Error example:
        {
            "data": null,
            "error": {
                "code": "VAL_001",
                "message": "Invalid configuration",
                "details": {"field": "model", "provided": "gpt-5.2"}
            },
            "meta": {"timestamp": "2026-01-23T12:00:00Z"}
        }
    """

    data: T | None = Field(None, description="Success payload, null on error")
    error: ErrorResponse | None = Field(
        None, description="Error information, null on success"
    )
    meta: MetaInfo = Field(..., description="Response metadata")

    @classmethod
    def success(cls, data: T) -> APIResponse[T]:
        """Create a success response with the given data."""
        return cls(data=data, error=None, meta=MetaInfo.now())

    @classmethod
    def failure(
        cls,
        code: str,
        message: str,
        *,
        field: str | None = None,
        provided: str | None = None,
        valid_options: list[str] | None = None,
    ) -> APIResponse[T]:
        """Create an error response."""
        details = None
        if field or provided or valid_options:
            details = ErrorDetails(
                field=field, provided=provided, valid_options=valid_options
            )
        return cls(
            data=None,
            error=ErrorResponse(code=code, message=message, details=details),
            meta=MetaInfo.now(),
        )


# Common error codes
class ErrorCodes:
    """Standard error codes for API responses."""

    # Validation errors (VAL_xxx)
    VAL_001 = "VAL_001"  # Invalid configuration
    VAL_002 = "VAL_002"  # Missing required field
    VAL_003 = "VAL_003"  # Invalid value

    # IO errors (IO_xxx)
    IO_001 = "IO_001"  # File not found
    IO_002 = "IO_002"  # Invalid JSON
    IO_003 = "IO_003"  # Permission denied

    # Solver errors (SOL_xxx)
    SOL_001 = "SOL_001"  # No solution found
    SOL_002 = "SOL_002"  # Timeout
    SOL_003 = "SOL_003"  # Invalid constraints
