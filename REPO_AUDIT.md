# Repo Audit vs Agent OS Standards
Date: 2026-01-27

Scope: `src/`, `pyproject.toml`, `README.md`, `config/`, `data/`, `tests/` (none found).

Scoring:
- 100: fully compliant
- 75: mostly compliant (minor gaps)
- 50: partial compliance (notable gaps)
- 25: major gaps
- 0: not implemented

Line references are 1-based.

## Architecture Standards

### Adapter Interface Protocol — 20/100 (Non-compliant)
Violations:
- Direct file I/O in core modules without protocol interfaces: `src/unicorn_armada/io.py:17`, `src/unicorn_armada/io.py:19`, `src/unicorn_armada/io.py:30`, `src/unicorn_armada/io.py:32`
- Surface layer writes outputs directly instead of via adapter interface: `src/unicorn_armada/cli.py:599`, `src/unicorn_armada/cli.py:600`, `src/unicorn_armada/cli.py:745`, `src/unicorn_armada/cli.py:746`
Notes: No protocol interfaces are defined for storage or external services.

### API Response Format — 0/100 (Non-compliant)
Violations:
- JSON outputs are raw payloads instead of `{data, error, meta}` envelope: `src/unicorn_armada/cli.py:599`, `src/unicorn_armada/cli.py:745`

### Log Line Format — 0/100 (Non-compliant)
Violations:
- CLI output uses free-form text instead of JSONL log schema: `src/unicorn_armada/cli.py:605`, `src/unicorn_armada/cli.py:615`

### Naming Conventions — 75/100 (Partial)
Violations:
- Inconsistent naming for diversity mode (`assist_type` vs `assistance`): `src/unicorn_armada/cli.py:509`, `src/unicorn_armada/combat.py:193`, `src/unicorn_armada/models.py:287`

### Thin Adapter Pattern — 20/100 (Non-compliant)
Violations:
- CLI contains core validation and domain logic instead of delegating to core layer: `src/unicorn_armada/cli.py:192`, `src/unicorn_armada/cli.py:316`, `src/unicorn_armada/cli.py:400`

## Global Standards

### Address Deprecations Immediately — 70/100 (Partial)
Notes:
- No deprecation suppressions found in `src/`.
- No CI or tool configuration found to treat deprecations as errors.

### Prefer Dependency Updates — 90/100 (Mostly compliant)
Evidence:
- Dependencies use non-pinned ranges: `pyproject.toml:7`, `pyproject.toml:8`, `pyproject.toml:9`
- `uv.lock` present for reproducibility.

## Python Standards

### Async-First Design — 0/100 (Non-compliant)
Violations:
- Core and CLI APIs are synchronous (`def`, not `async def`): `src/unicorn_armada/cli.py:462`, `src/unicorn_armada/cli.py:619`, `src/unicorn_armada/cli.py:779`, `src/unicorn_armada/solver.py:56`
- Blocking file I/O used in core and CLI: `src/unicorn_armada/io.py:19`, `src/unicorn_armada/cli.py:599`, `src/unicorn_armada/cli.py:746`

### Modern Python 3.14 — 35/100 (Non-compliant)
Violations:
- Project targets Python 3.13 instead of 3.14: `pyproject.toml:6`
- Legacy `Optional` typing used instead of `| None`:
  - `src/unicorn_armada/cli.py:6`
  - `src/unicorn_armada/cli.py:193`
  - `src/unicorn_armada/cli.py:194`
  - `src/unicorn_armada/cli.py:195`
  - `src/unicorn_armada/cli.py:196`
  - `src/unicorn_armada/cli.py:197`
  - `src/unicorn_armada/cli.py:198`
  - `src/unicorn_armada/cli.py:464`
  - `src/unicorn_armada/cli.py:467`
  - `src/unicorn_armada/cli.py:472`
  - `src/unicorn_armada/cli.py:477`
  - `src/unicorn_armada/cli.py:480`
  - `src/unicorn_armada/cli.py:485`
  - `src/unicorn_armada/cli.py:493`
  - `src/unicorn_armada/cli.py:504`
  - `src/unicorn_armada/cli.py:509`
  - `src/unicorn_armada/cli.py:621`
  - `src/unicorn_armada/cli.py:624`
  - `src/unicorn_armada/cli.py:629`
  - `src/unicorn_armada/cli.py:634`
  - `src/unicorn_armada/cli.py:637`
  - `src/unicorn_armada/cli.py:642`
  - `src/unicorn_armada/cli.py:781`
  - `src/unicorn_armada/cli.py:784`

### Pydantic-Only Schemas — 40/100 (Partial)
Violations:
- Dataclasses used for data models instead of Pydantic:
  - `src/unicorn_armada/benchmark.py:20`
  - `src/unicorn_armada/solver.py:16`
  - `src/unicorn_armada/solver.py:25`

### Strict Typing Enforcement — 25/100 (Non-compliant)
Violations:
- `object` used in type annotations: `src/unicorn_armada/cli.py:95`, `src/unicorn_armada/cli.py:97`, `src/unicorn_armada/cli.py:157`, `src/unicorn_armada/cli.py:675`
- Pydantic fields lack `Field(..., description=...)` (no descriptions present in models):
  - `src/unicorn_armada/models.py:49`
  - `src/unicorn_armada/models.py:59`
  - `src/unicorn_armada/models.py:92`
  - `src/unicorn_armada/models.py:146`
  - `src/unicorn_armada/models.py:151`
  - `src/unicorn_armada/models.py:217`
  - `src/unicorn_armada/models.py:241`
  - `src/unicorn_armada/models.py:258`
  - `src/unicorn_armada/models.py:283`
  - `src/unicorn_armada/models.py:290`
  - `src/unicorn_armada/models.py:309`
  - `src/unicorn_armada/models.py:316`
  - `src/unicorn_armada/models.py:324`
  - `src/unicorn_armada/models.py:332`
  - `src/unicorn_armada/models.py:344`

## Testing Standards

Note: No `tests/` directory found in the repository scan. All testing standards are currently non-compliant due to missing test structure and enforcement.

### Three-Tier Test Structure — 0/100 (Not implemented)
Violations:
- No `tests/unit`, `tests/integration`, or `tests/quality` directories present.

### BDD for Integration & Quality Tests — 0/100 (Not implemented)
Violations:
- No integration or quality tests present to follow Given/When/Then structure.

### Mandatory Coverage — 0/100 (Not implemented)
Violations:
- No tests or coverage configuration found.

### No Mocks for Quality Tests — 0/100 (Not implemented)
Violations:
- No quality test tier present.

### No Test Skipping — 0/100 (Not implemented)
Violations:
- No tests present; no enforcement of skip-free execution.

### Test Timing Rules — 0/100 (Not implemented)
Violations:
- No pytest tier markers or timing configuration found in repo config.
