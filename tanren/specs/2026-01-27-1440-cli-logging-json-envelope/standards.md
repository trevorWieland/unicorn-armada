# Standards for CLI Structured Logging + JSON Envelope

The following standards apply to this work.

---

## architecture/api-response-format

# API Response Format

All CLI JSON responses use `{data, error, meta}` envelope structure. Each field is a clearly defined Pydantic model.

```python
from pydantic import BaseModel, Field

# ✓ Good: Clear Pydantic models for envelope fields
class MetaInfo(BaseModel):
    """Metadata for API responses."""
    timestamp: str = Field(..., description="ISO-8601 timestamp")

class ErrorDetails(BaseModel):
    """Detailed error context."""
    field: str | None = Field(None, description="Field name if validation error")
    provided: str | None = Field(None, description="Value that was provided")
    valid_options: list[str] | None = Field(None, description="Valid values if applicable")

class ErrorResponse(BaseModel):
    """Error information in response."""
    code: str = Field(..., description="Error code (e.g., VAL_001)")
    message: str = Field(..., description="Human-readable error message")
    details: ErrorDetails | None = Field(None, description="Additional error context")

class APIResponse[T](BaseModel, Generic[T]):
    """Generic API response envelope."""
    data: T | None = Field(None, description="Success payload, null on error")
    error: ErrorResponse | None = Field(None, description="Error information, null on success")
    meta: MetaInfo = Field(..., description="Response metadata")
```

```json
// ✓ Good: Success response with Pydantic-validated types
{
  "data": {
    "run_id": "abc123",
    "status": "running",
    "phase": "translate"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-01-23T12:00:00Z"
  }
}

// ✓ Good: Error response with Pydantic-validated types
{
  "data": null,
  "error": {
    "code": "VAL_001",
    "message": "Invalid configuration: model not found",
    "details": {
      "field": "model",
      "provided": "gpt-5.2",
      "valid_options": ["gpt-4", "gpt-4.1", "gpt-4o"]
    }
  },
  "meta": {
    "timestamp": "2026-01-23T12:00:00Z"
  }
}

// ✗ Bad: Raw data without envelope
{
  "run_id": "abc123",
  "status": "running"
}

// ✗ Bad: Error without code or structure
{
  "error": "Something went wrong"
}
```

**Response envelope Pydantic model:**
- `data[T]`: Generic type containing success payload, null on error
- `error`: `ErrorResponse` model with `{code, message, details}`, null on success
- `meta`: `MetaInfo` or similar for audit metadata

**Error Pydantic model requirements:**
- `code`: Error identifier (e.g., `VAL_001`, `AUTH_001`, `DB_001`) as required string
- `message`: Human-readable error description as required string
- `details`: Optional `ErrorDetails` or similar for additional context

**Meta Pydantic model requirements:**
- Include timestamp for auditability
- Add version, request_id, or other metadata as needed

**Success response requirements:**
- Always include `data` field with typed payload
- `error` field must be `None` (never omitted in Pydantic model)
- Include `meta` with timestamp for auditability

**Error response requirements:**
- Always include both `code` and `message` in error model
- Include `details` when helpful (field names, valid options, suggestions)
- `data` field must be `None` (never omitted in Pydantic model)

**Exceptions (streaming/event-driven):**
Streaming responses and event-driven outputs (e.g., JSONL logs, SSE events) may use different structures as they don't fit single-response envelope.

**Why:** Frontend always knows where to find data or errors, consistent parsing without guessing schema per endpoint, predictable error handling, and type safety through Pydantic validation.

---

## architecture/log-line-format

# Log Line Format

All log lines use stable JSONL schema with `{timestamp, level, event, run_id, phase, message, data}` fields.

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

# ✓ Good: Stable Pydantic model for log lines
class LogEntry(BaseModel):
    """Single log line in JSONL format."""
    timestamp: str = Field(..., description="ISO-8601 timestamp")
    level: Literal["debug", "info", "warn", "error"] = Field(
        ..., description="Log level"
    )
    event: str = Field(..., description="Event type (e.g., run_started, phase_completed)")
    run_id: str = Field(..., description="Pipeline run identifier")
    phase: str | None = Field(None, description="Pipeline phase (e.g., translate, qa)")
    message: str = Field(..., description="Human-readable log message")
    data: dict | None = Field(None, description="Structured event data")

# ✓ Good: Writing log lines
def write_log(entry: LogEntry) -> None:
    """Write log line to JSONL file."""
    with open("logs/pipeline.log", "a") as f:
        f.write(entry.model_dump_json() + "\n")
```

```json
// ✓ Good: Log line examples
{"timestamp":"2026-01-23T12:00:00Z","level":"info","event":"run_started","run_id":"abc123","phase":null,"message":"Pipeline started","data":{"config_file":"rentl.toml"}}
{"timestamp":"2026-01-23T12:01:00Z","level":"info","event":"phase_completed","run_id":"abc123","phase":"translate","message":"Translation phase completed","data":{"lines_translated":1234,"duration_s":45.2}}
{"timestamp":"2026-01-23T12:02:00Z","level":"error","event":"translation_failed","run_id":"abc123","phase":"translate","message":"Translation failed for scene 42","data":{"scene_id":42,"error_code":"RATE_LIMIT","retry_count":3}}
```

**Log line Pydantic model requirements:**
- `timestamp`: ISO-8601 timestamp string (required)
- `level`: One of `debug`, `info`, `warn`, `error` (required)
- `event`: Event name in `snake_case` (required)
- `run_id`: Pipeline run identifier (required)
- `phase`: Pipeline phase name or `None` (optional)
- `message`: Human-readable log message (required)
- `data`: Structured event data as dict or `None` (optional)

**JSONL format:**
- One JSON object per line
- Lines separated by newlines
- No outer array or object wrapper
- UTF-8 encoding

**Event naming conventions:**
- Use `snake_case` for event names
- Examples: `run_started`, `phase_completed`, `translation_finished`, `error_occurred`
- Prefix with phase name when applicable: `translate_completed`, `qa_failed`

**Level usage guidelines:**
- `debug`: Detailed diagnostics for development
- `info`: Normal operational messages (phase starts/completions)
- `warn`: Recoverable issues (retries, fallbacks)
- `error`: Failures requiring attention

**Exceptions (external logging systems):**
When integrating with external logging systems (e.g., cloud logging services, ELK stacks), follow their schema requirements but map required fields where possible.

**Why:** Consistent log parsing for observability tools and dashboards; enables easy log analysis and filtering; structured data is machine-readable and queryable.

---

## architecture/thin-adapter-pattern

# Thin Adapter Pattern

Surface layers (CLI, TUI, API, etc.) are **thin adapters only**. All business logic lives in the **Core Domain** packages.

```python
# ✓ Good: CLI is a thin wrapper
def run_pipeline(run_id: str):
    """Start pipeline run - thin adapter over core API."""
    # Calls Core Domain API directly
    result = await pipeline_runner.start_run(run_id)
    return format_json_output(result)

# ✗ Bad: Business logic in CLI
def run_pipeline(run_id: str):
    """Start pipeline run - contains core logic."""
    validate_config(config)  # Business logic
    context = build_context(sources)  # Business logic
    result = translate(context)  # Business logic
    return result
```

**Core Domain logic includes:**
- Pipeline orchestration and phase execution
- Data transformation and validation
- Agent orchestration
- Storage operations
- Model integration

**Surface layers may contain:**
- Command definitions and argument parsing
- Output formatting (pretty-print, JSON wrapper)
- Truly surface-specific features that will never be reused

**Even validation and formatting should use contract models from the Core Domain** - never duplicate schemas or business rules.

**Why:** Ensures core logic is reusable across any surface (CLI, TUI, API, Lambda) without duplication and makes testing easier (test core once, surfaces are just IO wrappers).
