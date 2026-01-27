# Phase 1: Code Quality Standards Alignment

## Overview

Align the unicorn-armada codebase with Agent OS standards, focusing on code quality before testing infrastructure.

**Scope:** 11 of 18 standards (Architecture, Global, Python)
**Phase 2:** Testing standards (6 remaining)

## Task List

### Task 1: Save Spec Documentation
**Status:** Complete
**Priority:** High

Create spec folder with plan, shape, standards, and references documentation.

---

### Task 2: Upgrade to Python 3.14 and Modern Syntax
**Status:** Pending
**Priority:** High
**Standard:** `python/modern-python-314`

- Update `pyproject.toml` to require Python 3.14
- Replace all `Optional[T]` with `T | None` (24+ occurrences)
- Replace `Union[T, U]` with `T | U` if any exist
- Use `dict1 | dict2` instead of unpacking where applicable

**Files:**
- `pyproject.toml`
- `src/unicorn_armada/cli.py`
- All source files with legacy typing

---

### Task 3: Convert Dataclasses to Pydantic
**Status:** Pending
**Priority:** High
**Standard:** `python/pydantic-only-schemas`

- Convert dataclasses to Pydantic BaseModel
- Ensure all fields have `Field(..., description="...")`

**Files:**
- `src/unicorn_armada/benchmark.py:20`
- `src/unicorn_armada/solver.py:16, 25`

---

### Task 4: Enforce Strict Typing
**Status:** Pending
**Priority:** High
**Standard:** `python/strict-typing-enforcement`

- Remove `object` types - replace with explicit types
- Add `Field(..., description="...")` to all Pydantic model fields
- Run `ty --strict` and fix remaining type errors

**Files:**
- `src/unicorn_armada/cli.py:95, 97, 157, 675`
- `src/unicorn_armada/models.py` (15+ fields missing descriptions)

---

### Task 5: Fix Naming Inconsistencies
**Status:** Pending
**Priority:** Medium
**Standard:** `architecture/naming-conventions`

- Align `assist_type` vs `assistance` naming
- Choose one canonical name and update all references

**Files:**
- `src/unicorn_armada/cli.py:509`
- `src/unicorn_armada/combat.py:193`
- `src/unicorn_armada/models.py:287`

---

### Task 6: Refactor to Thin Adapter Pattern
**Status:** Pending
**Priority:** High
**Standard:** `architecture/thin-adapter-pattern`

- Extract business logic from CLI into core modules
- CLI should only: parse args, call core functions, format output
- Create core API functions that CLI delegates to

**Files:**
- `src/unicorn_armada/cli.py:192, 316, 400`
- Potentially new `src/unicorn_armada/core.py`

---

### Task 7: Implement Protocol Interfaces for IO
**Status:** Pending
**Priority:** High
**Standard:** `architecture/adapter-interface-protocol`

- Define `StorageProtocol` for file I/O
- Refactor `io.py` to use protocol interface
- CLI uses protocol interface instead of direct file writes

**Files:**
- `src/unicorn_armada/io.py:17, 19, 30, 32`
- `src/unicorn_armada/cli.py`
- New `src/unicorn_armada/protocols.py`

---

### Task 8: Implement API Response Envelope
**Status:** Pending
**Priority:** High
**Standard:** `architecture/api-response-format`

- Create `APIResponse[T]`, `ErrorResponse`, `MetaInfo` Pydantic models
- Wrap JSON outputs in `{data, error, meta}` envelope
- Add error codes for validation and runtime errors

**Files:**
- `src/unicorn_armada/cli.py:599, 745`
- New response models

---

### Task 9: Implement Structured JSONL Logging
**Status:** Pending
**Priority:** Medium
**Standard:** `architecture/log-line-format`

- Create `LogEntry` Pydantic model with required fields
- Replace free-form text output with JSONL log entries
- Add `run_id`, `event`, `level`, `timestamp` to log lines

**Files:**
- `src/unicorn_armada/cli.py:605, 615`
- New logging infrastructure

---

### Task 10: Convert to Async-First Design
**Status:** Pending
**Priority:** High
**Standard:** `python/async-first-design`

- Convert core functions to `async def`
- Convert file I/O to async
- Use `asyncio.run()` in CLI entry points
- Consider `asyncio.gather()` for parallel operations

**Files:**
- `src/unicorn_armada/cli.py:462, 619, 779`
- `src/unicorn_armada/solver.py:56`
- `src/unicorn_armada/io.py:19`
- All source files

---

### Task 11: Configure Deprecation Enforcement
**Status:** Pending
**Priority:** Medium
**Standard:** `global/address-deprecations-immediately`

- Configure ruff/ty to treat deprecation warnings as errors
- Add CI check for deprecation warnings
- Verify no existing deprecation suppressions

**Files:**
- `pyproject.toml`
- CI configuration

---

### Task 12: Validate Dependency Strategy
**Status:** Pending
**Priority:** Low
**Standard:** `global/prefer-dependency-updates`

- Confirm version ranges are non-pinned (already 90% compliant)
- Ensure `uv.lock` is committed for reproducibility
- Document `uv sync --upgrade` workflow

**Files:**
- `pyproject.toml`
- `uv.lock`

---

## Expected Outcomes

After Phase 1 completion:

1. **Python 3.14 compliant** - Modern type syntax throughout
2. **All Pydantic schemas** - No dataclasses, all fields documented
3. **Strict typing** - No `object` or `Any` types
4. **Thin CLI adapter** - Business logic in core modules
5. **Protocol interfaces** - IO abstracted for testability
6. **Structured output** - JSON envelope and JSONL logging
7. **Async-first** - Ready for parallel operations
8. **Clean tooling** - Deprecation enforcement configured

## Phase 2 Preview

Testing infrastructure with 6 standards:
- `testing/three-tier-test-structure`
- `testing/bdd-for-integration-quality`
- `testing/mandatory-coverage`
- `testing/no-mocks-for-quality-tests`
- `testing/no-test-skipping`
- `testing/test-timing-rules`
