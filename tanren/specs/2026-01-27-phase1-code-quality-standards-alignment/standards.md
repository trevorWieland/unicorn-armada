# Standards for Phase 1: Code Quality Standards Alignment

The following standards apply to this work. Full content included for reference during implementation.

---

## architecture/adapter-interface-protocol

Never access infrastructure adapters directly. Always access storage, models, and external services through **Protocol Interfaces** defined in the Core Domain packages.

```python
# Good: Access through protocol interface
from core.adapters.vector import VectorStoreProtocol

async def search_context(query: str, vector_store: VectorStoreProtocol):
    """Search vector context via protocol - implementation agnostic."""
    return await vector_store.search(query)

# Bad: Direct access to implementation
import chromadb

async def search_context(query: str):
    """Search vector context - hardcoded to Chroma."""
    client = chromadb.Client()
    collection = client.get_collection("context")
    return collection.query(query)
```

**Pattern Structure:**
1. **Define Protocol**: `core.ports.VectorStoreProtocol` (The contract)
2. **Implement Adapter**: `infrastructure.adapters.chroma.ChromaVectorStore` (The specific tech)
3. **Inject Dependency**: Pass the adapter where the protocol is expected

**Common Protocols:**
- `VectorStoreProtocol` - Vector storage and retrieval
- `ModelClientProtocol` - LLM model integration
- `StorageProtocol` - Metadata and artifact storage

**Why:** Enables swapping implementations without changing business logic, makes testing easier with mock protocols, and keeps the core domain clean of infrastructure concerns.

---

## architecture/api-response-format

All CLI JSON responses use `{data, error, meta}` envelope structure. Each field is a clearly defined Pydantic model.

```python
from pydantic import BaseModel, Field

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

**Success response:**
```json
{
  "data": {"run_id": "abc123", "status": "running"},
  "error": null,
  "meta": {"timestamp": "2026-01-23T12:00:00Z"}
}
```

**Error response:**
```json
{
  "data": null,
  "error": {
    "code": "VAL_001",
    "message": "Invalid configuration",
    "details": {"field": "model", "provided": "gpt-5.2"}
  },
  "meta": {"timestamp": "2026-01-23T12:00:00Z"}
}
```

**Why:** Frontend always knows where to find data or errors, consistent parsing, predictable error handling, and type safety through Pydantic validation.

---

## architecture/log-line-format

All log lines use stable JSONL schema with `{timestamp, level, event, run_id, phase, message, data}` fields.

```python
from pydantic import BaseModel, Field
from typing import Literal

class LogEntry(BaseModel):
    """Single log line in JSONL format."""
    timestamp: str = Field(..., description="ISO-8601 timestamp")
    level: Literal["debug", "info", "warn", "error"] = Field(..., description="Log level")
    event: str = Field(..., description="Event type (e.g., run_started, phase_completed)")
    run_id: str = Field(..., description="Pipeline run identifier")
    phase: str | None = Field(None, description="Pipeline phase (e.g., translate, qa)")
    message: str = Field(..., description="Human-readable log message")
    data: dict | None = Field(None, description="Structured event data")
```

**JSONL format:**
- One JSON object per line
- Lines separated by newlines
- No outer array or object wrapper
- UTF-8 encoding

**Event naming:** Use `snake_case` (e.g., `run_started`, `phase_completed`, `error_occurred`)

**Level usage:**
- `debug`: Detailed diagnostics
- `info`: Normal operational messages
- `warn`: Recoverable issues
- `error`: Failures requiring attention

**Why:** Consistent log parsing for observability tools; structured data is machine-readable and queryable.

---

## architecture/naming-conventions

Use consistent naming conventions across all code. Never mix styles.

**Python code naming:**
- Modules/files: `snake_case.py`
- Functions/variables: `snake_case`
- Classes/types: `PascalCase`

**Database naming:**
- Tables/collections: `snake_case`
- Columns/fields: `snake_case`
- Foreign keys: `{entity}_id`

**API naming:**
- CLI commands: `kebab-case`
- CLI options: `--snake-case`

**JSON/JSONL naming:**
- Fields: `snake_case`

**Why:** Consistency makes code predictable and easier to navigate.

---

## architecture/thin-adapter-pattern

Surface layers (CLI, TUI, API, etc.) are **thin adapters only**. All business logic lives in the **Core Domain** packages.

```python
# Good: CLI is a thin wrapper
def run_pipeline(run_id: str):
    """Start pipeline run - thin adapter over core API."""
    result = await pipeline_runner.start_run(run_id)
    return format_json_output(result)

# Bad: Business logic in CLI
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

**Why:** Ensures core logic is reusable across any surface (CLI, TUI, API, Lambda) without duplication.

---

## global/address-deprecations-immediately

Deprecation warnings must be addressed immediately. Never defer to future work.

```python
# Good: Fix deprecation immediately
from datetime import datetime, timezone
current_time = datetime.now(timezone.utc)

# Bad: Ignore deprecation
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
current_time = datetime.utcnow()  # Deprecated
```

**Deprecation handling:**
- Run linters/CI with deprecation warnings as errors
- Fix deprecation warnings immediately when detected
- Replace deprecated APIs with recommended alternatives

**CI configuration:**
- Treat deprecation warnings as errors in CI
- Block PRs that introduce new deprecation warnings

**Why:** Prevents technical debt and ensures smooth upgrades.

---

## global/prefer-dependency-updates

Prefer frequent dependency updates to stay on latest stable features and performance.

```toml
# Good: Non-pinned ranges
[dependencies]
pydantic = ">=2.0,<3.0"
openai = "^2.11.0"

# Bad: Pinned versions
[dependencies]
pydantic = "==2.1.3"
```

**Update strategy:**
- Use compatible version ranges instead of exact pins
- Update dependencies regularly with `uv sync --upgrade`
- `uv.lock` records exact versions for reproducibility

**Why:** Get security fixes promptly, stay on latest features, avoid outdated dependency debt.

---

## python/async-first-design

Design all APIs and I/O around `async`/`await` and modern structured concurrency.

```python
# Good: Async-first API
async def translate_scenes(request: TranslationRequest) -> list[str]:
    """Translate scenes in parallel using structured concurrency."""
    tasks = [translate_scene(scene) for scene in request.scenes]
    return await asyncio.gather(*tasks)

# Bad: Blocking I/O
def translate_scenes(request: TranslationRequest) -> list[str]:
    """Translate scenes sequentially - blocks on network IO."""
    results = []
    for scene in request.scenes:
        results.append(translate_scene_sync(scene))
    return results
```

**Async requirements:**
- All I/O operations use `async`/`await`
- Design APIs to be callable from async contexts
- Use `asyncio.gather`, `asyncio.TaskGroup` for concurrency
- Avoid blocking operations in async paths

**Exceptions (entry points only):**
- Script entry points may use synchronous wrappers
- Must bridge to async code immediately (e.g., `asyncio.run()`)

**Why:** Enables parallel execution, handles network IO efficiently, scales without blocking.

---

## python/modern-python-314

Use Python 3.14 features and patterns. Avoid legacy constructs.

```python
# Good: Modern Python 3.14
result: str | None  # Type unions
config = base_config | custom_config  # Dictionary union
print(f"{result=}")  # f-string debugging

match phase:
    case "translate":
        await translate()
    case "qa":
        await run_qa()

# Bad: Legacy patterns
result: Optional[str]  # Old-style
config = {**base_config, **custom_config}  # Old unpacking
```

**Modern features to use:**
- Type unions: `str | None` instead of `Union[str, None]`
- Pattern matching: `match/case` instead of if/elif chains
- Dictionary union: `dict1 | dict2`
- f-string debugging: `f"{var=}"`
- Async generators

**Legacy patterns to avoid:**
- `Optional[T]`, `Union[T, U]`
- `typing.List`, `typing.Dict`
- `{**d1, **d2}`

**Why:** Cleaner syntax, better expressiveness, performance improvements.

---

## python/pydantic-only-schemas

Never use dataclasses or plain classes for schemas. All schemas must use Pydantic.

```python
# Good: Pydantic schema
from pydantic import BaseModel, Field

class TranslationRequest(BaseModel):
    source_text: str = Field(..., min_length=1, description="Text to translate")
    target_language: str = Field(..., pattern=r'^[a-z]{2}$', description="ISO 639-1 code")

# Bad: dataclass
from dataclasses import dataclass

@dataclass
class TranslationRequest:
    source_text: str  # No validation, no serialization
    target_language: str
```

**When to use Pydantic:**
- API request/response models
- Configuration models
- Agent input/output schemas
- Storage document models
- Any data that crosses package boundaries

**Why:** Pydantic provides automatic validation, native JSON serialization, better type inference.

---

## python/strict-typing-enforcement

Never use `Any` or `object` in types. Always model explicit schema types.

```python
# Good: Explicit types
from pydantic import BaseModel, Field

class TranslationRequest(BaseModel):
    source_text: str
    target_language: str
    model: str = Field(..., description="Model identifier")

def translate(request: TranslationRequest) -> TranslationResult:
    """Translate with explicit types."""
    ...

# Bad: Any or object
from typing import Any

def translate(request: Any) -> Any:
    """No type safety."""
    ...
```

**Pydantic fields:**
- Every field must use `Field(..., description="...")`
- Use built-in validators (`min_length`, `max_length`, `pattern`, `gt`, `ge`, `lt`, `le`)
- Never use raw type annotation without Field for schema fields

**Exceptions (extremely rare):**
`Any` or `object` only when fully external library/API and creating types isn't practical.

**Why:** Catches type errors at dev time, makes code self-documenting, prevents bugs.
