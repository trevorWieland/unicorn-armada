# References for Phase 1: Code Quality Standards Alignment

## Audit Violations

These are the specific violations identified in `REPO_AUDIT.md` that this spec addresses.

### Architecture Violations

#### Adapter Interface Protocol (20/100)
- Direct file I/O without protocol interfaces:
  - `src/unicorn_armada/io.py:17`
  - `src/unicorn_armada/io.py:19`
  - `src/unicorn_armada/io.py:30`
  - `src/unicorn_armada/io.py:32`
- Surface layer writes directly instead of via adapter:
  - `src/unicorn_armada/cli.py:599`
  - `src/unicorn_armada/cli.py:600`
  - `src/unicorn_armada/cli.py:745`
  - `src/unicorn_armada/cli.py:746`

#### API Response Format (0/100)
- JSON outputs are raw payloads instead of `{data, error, meta}` envelope:
  - `src/unicorn_armada/cli.py:599`
  - `src/unicorn_armada/cli.py:745`

#### Log Line Format (0/100)
- CLI output uses free-form text instead of JSONL:
  - `src/unicorn_armada/cli.py:605`
  - `src/unicorn_armada/cli.py:615`

#### Naming Conventions (75/100)
- Inconsistent naming for diversity mode:
  - `src/unicorn_armada/cli.py:509` (`assist_type`)
  - `src/unicorn_armada/combat.py:193` (naming variant)
  - `src/unicorn_armada/models.py:287` (naming variant)

#### Thin Adapter Pattern (20/100)
- CLI contains core validation and domain logic:
  - `src/unicorn_armada/cli.py:192`
  - `src/unicorn_armada/cli.py:316`
  - `src/unicorn_armada/cli.py:400`

### Python Violations

#### Async-First Design (0/100)
- Synchronous core and CLI APIs:
  - `src/unicorn_armada/cli.py:462`
  - `src/unicorn_armada/cli.py:619`
  - `src/unicorn_armada/cli.py:779`
  - `src/unicorn_armada/solver.py:56`
- Blocking file I/O:
  - `src/unicorn_armada/io.py:19`
  - `src/unicorn_armada/cli.py:599`
  - `src/unicorn_armada/cli.py:746`

#### Modern Python 3.14 (35/100)
- Project targets Python 3.13: `pyproject.toml:6`
- Legacy `Optional` typing (24 occurrences in cli.py):
  - Lines 6, 193-198, 464, 467, 472, 477, 480, 485, 493, 504, 509, 621, 624, 629, 634, 637, 642, 781, 784

#### Pydantic-Only Schemas (40/100)
- Dataclasses used instead of Pydantic:
  - `src/unicorn_armada/benchmark.py:20`
  - `src/unicorn_armada/solver.py:16`
  - `src/unicorn_armada/solver.py:25`

#### Strict Typing Enforcement (25/100)
- `object` used in type annotations:
  - `src/unicorn_armada/cli.py:95`
  - `src/unicorn_armada/cli.py:97`
  - `src/unicorn_armada/cli.py:157`
  - `src/unicorn_armada/cli.py:675`
- Pydantic fields lack `Field(..., description=...)`:
  - `src/unicorn_armada/models.py:49, 59, 92, 146, 151, 217, 241, 258, 283, 290, 309, 316, 324, 332, 344`

### Global Violations

#### Address Deprecations Immediately (70/100)
- No CI or tool configuration to treat deprecations as errors
- No deprecation suppressions found (good)

#### Prefer Dependency Updates (90/100)
- Already mostly compliant
- Dependencies use non-pinned ranges
- `uv.lock` present for reproducibility

## Standards Examples

All implementation patterns are drawn from the standards documentation in `agent-os/standards/`. Key examples:

- **Protocol pattern:** See `architecture/adapter-interface-protocol.md` for `VectorStoreProtocol` example
- **API envelope:** See `architecture/api-response-format.md` for `APIResponse[T]` generic model
- **JSONL logging:** See `architecture/log-line-format.md` for `LogEntry` model
- **Async patterns:** See `python/async-first-design.md` for `asyncio.gather()` usage
- **Modern typing:** See `python/modern-python-314.md` for `T | None` syntax
- **Pydantic fields:** See `python/strict-typing-enforcement.md` for `Field(description=...)` pattern
