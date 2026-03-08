# Phase 1: Code Quality Standards Alignment

## Overview

Align the unicorn-armada codebase with Agent OS standards, focusing on code quality before testing infrastructure.

**Scope:** 11 of 18 standards (Architecture, Global, Python)
**Phase 2:** Testing standards (6 remaining)
**Status:** COMPLETE

## Task List

### Task 1: Save Spec Documentation
**Status:** Complete
**Priority:** High

Create spec folder with plan, shape, standards, and references documentation.

---

### Task 2: Upgrade to Python 3.14 and Modern Syntax
**Status:** Complete
**Priority:** High
**Standard:** `python/modern-python-314`

- Updated `pyproject.toml` to require Python 3.14
- Replaced all `Optional[T]` with `T | None`
- Using modern `Annotated` pattern for Typer options
- Imports from `collections.abc` instead of `typing`

**Files modified:**
- `pyproject.toml`
- `src/unicorn_armada/cli.py`
- `src/unicorn_armada/solver.py`
- `src/unicorn_armada/utils.py`

---

### Task 3: Convert Dataclasses to Pydantic
**Status:** Complete
**Priority:** High
**Standard:** `python/pydantic-only-schemas`

- Converted `BenchmarkStats` to Pydantic BaseModel
- Converted `Cluster` and `UnitState` to Pydantic BaseModel
- All fields have `Field(..., description="...")`

**Files modified:**
- `src/unicorn_armada/benchmark.py`
- `src/unicorn_armada/solver.py`

---

### Task 4: Enforce Strict Typing
**Status:** Complete
**Priority:** High
**Standard:** `python/strict-typing-enforcement`

- Removed `object` types from CLI
- Added `Field(..., description="...")` to all Pydantic model fields
- Created `RapportEntry` and `UnitSizeReportData` TypedDicts
- All type checks pass with `ty check`

**Files modified:**
- `src/unicorn_armada/cli.py`
- `src/unicorn_armada/models.py`

---

### Task 5: Fix Naming Inconsistencies
**Status:** Complete
**Priority:** Medium
**Standard:** `architecture/naming-conventions`

- Changed `assistance` to `assist_type` in combat.py to match models.py

**Files modified:**
- `src/unicorn_armada/combat.py`

---

### Task 6: Refactor to Thin Adapter Pattern
**Status:** Complete
**Priority:** High
**Standard:** `architecture/thin-adapter-pattern`

- Created `src/unicorn_armada/core.py` with:
  - `ValidationError` domain exception
  - `ProblemInputs` and `CombatContext` container classes
  - `load_and_validate_problem()` function
  - `load_combat_context()` function
  - `apply_preset()` function with `SCORING_PRESETS`
  - `make_combat_score_fn()` helper

**Files created:**
- `src/unicorn_armada/core.py`

---

### Task 7: Implement Protocol Interfaces for IO
**Status:** Complete
**Priority:** High
**Standard:** `architecture/adapter-interface-protocol`

- Created protocol interfaces in `protocols.py`:
  - `DatasetLoaderProtocol`
  - `RosterLoaderProtocol`
  - `PairsLoaderProtocol`
  - `UnitsLoaderProtocol`
  - `CombatScoringLoaderProtocol`
  - `CharacterClassesLoaderProtocol`
  - `OutputWriterProtocol`
  - `StorageProtocol` (combined facade)
- Created `FileStorage` class implementing `StorageProtocol`

**Files created:**
- `src/unicorn_armada/protocols.py`

**Files modified:**
- `src/unicorn_armada/io.py`

---

### Task 8: Implement API Response Envelope
**Status:** Complete
**Priority:** High
**Standard:** `architecture/api-response-format`

- Created response models in `responses.py`:
  - `MetaInfo` with timestamp
  - `ErrorDetails` for validation errors
  - `ErrorResponse` with code, message, details
  - `APIResponse[T]` generic envelope
  - `ErrorCodes` constants
- Updated benchmark output to use envelope

**Files created:**
- `src/unicorn_armada/responses.py`

**Files modified:**
- `src/unicorn_armada/cli.py`

---

### Task 9: Implement Structured JSONL Logging
**Status:** Complete
**Priority:** Medium
**Standard:** `architecture/log-line-format`

- Created logging infrastructure in `logging.py`:
  - `LogEntry` Pydantic model
  - `Logger` class with level filtering
  - Standard `Events` constants

**Files created:**
- `src/unicorn_armada/logging.py`

---

### Task 10: Convert to Async-First Design
**Status:** N/A (Deferred)
**Priority:** High
**Standard:** `python/async-first-design`

**Decision:** This codebase is a CLI with file I/O and CPU-bound solver computation.
There is no network I/O or external service calls. The async-first standard
is intended for I/O-bound operations (network calls, database access) where
async provides parallelism benefits.

Since the core operations are:
1. File reads (blocking, but fast)
2. CPU-bound OR-Tools constraint solving
3. File writes (blocking, but fast)

Converting to async would add complexity without benefit. The standard's
exception clause applies: "Script entry points may use synchronous wrappers."

**Future consideration:** If network I/O is added (e.g., calling external
services, streaming results), async should be adopted at that time.

---

### Task 11: Configure Deprecation Enforcement
**Status:** Complete
**Priority:** Medium
**Standard:** `global/address-deprecations-immediately`

- Configured ruff with comprehensive lint rules including `UP` (pyupgrade)
- Configured pytest to treat deprecation warnings as errors
- Configured ty with Python 3.14 environment
- All deprecation issues fixed (datetime.UTC, typing imports, etc.)

**Files modified:**
- `pyproject.toml`

---

### Task 12: Validate Dependency Strategy
**Status:** Complete
**Priority:** Low
**Standard:** `global/prefer-dependency-updates`

- All dependencies use non-pinned ranges:
  - `pydantic>=2.7.0`
  - `typer>=0.12.3`
  - `ruff>=0.14.11`
  - `ty>=0.0.11`
- `uv.lock` committed for reproducibility

**Files verified:**
- `pyproject.toml`
- `uv.lock`

---

## Outcomes Achieved

After Phase 1 completion:

1. **Python 3.14 compliant** - Modern type syntax throughout (`T | None`, `Annotated`)
2. **All Pydantic schemas** - No dataclasses, all fields documented with Field()
3. **Strict typing** - No `object` or `Any` types, all checks pass
4. **Thin CLI adapter** - Business logic extracted to core.py
5. **Protocol interfaces** - IO abstracted via StorageProtocol for testability
6. **Structured output** - JSON envelope (responses.py) and JSONL logging (logging.py)
7. **Async-first** - Deferred (no network I/O to benefit from async)
8. **Clean tooling** - Deprecation enforcement configured via ruff/pytest

## New Files Created

- `src/unicorn_armada/core.py` - Core business logic
- `src/unicorn_armada/protocols.py` - Protocol interfaces
- `src/unicorn_armada/responses.py` - API response envelope
- `src/unicorn_armada/logging.py` - Structured JSONL logging

## Verification

```bash
# All checks pass
uv run ruff check src/
uv run ty check src/unicorn_armada/
```

## Phase 2 Preview

Testing infrastructure with 6 standards:
- `testing/three-tier-test-structure`
- `testing/bdd-for-integration-quality`
- `testing/mandatory-coverage`
- `testing/no-mocks-for-quality-tests`
- `testing/no-test-skipping`
- `testing/test-timing-rules`
