# Phase 1: Code Quality Standards Alignment - Shaping Notes

## Scope

Align the unicorn-armada codebase with 11 Agent OS standards covering architecture, global practices, and Python patterns. This is Phase 1 of a two-phase effort; Phase 2 will address testing infrastructure.

### Standards in Scope

**Architecture (5):**
1. `adapter-interface-protocol` - Protocol interfaces for IO/storage
2. `api-response-format` - `{data, error, meta}` envelope for JSON
3. `log-line-format` - JSONL structured logging
4. `naming-conventions` - Fix inconsistent naming
5. `thin-adapter-pattern` - Move business logic out of CLI

**Global (2):**
6. `address-deprecations-immediately` - CI enforcement
7. `prefer-dependency-updates` - Already 90% compliant

**Python (4):**
8. `async-first-design` - Convert to async/await
9. `modern-python-314` - Upgrade to 3.14, remove `Optional[]`
10. `pydantic-only-schemas` - Convert dataclasses to Pydantic
11. `strict-typing-enforcement` - Remove `object`, add `Field(description=...)`

## Decisions

- **Phased approach:** Code quality first (Phase 1), testing infrastructure second (Phase 2)
- **Order of operations:** Foundational changes (Python version, typing) before architectural refactoring
- **Async conversion:** Full async-first conversion, using `asyncio.run()` at CLI entry points
- **Protocol pattern:** Create `protocols.py` for interface definitions
- **Naming resolution:** Will need to investigate `assist_type` vs `assistance` usage to pick canonical name

## Context

- **Visuals:** None
- **References:** Standards examples only (no existing refactored code to reference)
- **Product alignment:** Confirmed alignment with roadmap ("Audit alignment" is planned work)

## Standards Applied

| Standard | Why It Applies |
|----------|----------------|
| `adapter-interface-protocol` | Direct file I/O in core modules without protocols |
| `api-response-format` | JSON outputs are raw payloads without envelope |
| `log-line-format` | CLI uses free-form text instead of JSONL |
| `naming-conventions` | Inconsistent `assist_type` vs `assistance` naming |
| `thin-adapter-pattern` | CLI contains core validation and domain logic |
| `address-deprecations-immediately` | No CI enforcement for deprecations |
| `prefer-dependency-updates` | Already mostly compliant (90%) |
| `async-first-design` | All APIs are synchronous |
| `modern-python-314` | Project targets 3.13, uses legacy `Optional[]` |
| `pydantic-only-schemas` | Dataclasses used in benchmark.py, solver.py |
| `strict-typing-enforcement` | `object` types used, Pydantic fields lack descriptions |

## Audit Summary

From `REPO_AUDIT.md` dated 2026-01-27:

| Category | Standard | Score |
|----------|----------|-------|
| Architecture | Adapter Interface Protocol | 20/100 |
| Architecture | API Response Format | 0/100 |
| Architecture | Log Line Format | 0/100 |
| Architecture | Naming Conventions | 75/100 |
| Architecture | Thin Adapter Pattern | 20/100 |
| Global | Address Deprecations | 70/100 |
| Global | Prefer Dependency Updates | 90/100 |
| Python | Async-First Design | 0/100 |
| Python | Modern Python 3.14 | 35/100 |
| Python | Pydantic-Only Schemas | 40/100 |
| Python | Strict Typing Enforcement | 25/100 |

## Future Considerations

- **TUI readiness:** Thin adapter pattern refactoring will make future Textual TUI easier to add
- **Testability:** Protocol interfaces will enable mocking in unit tests (Phase 2)
- **Parallel operations:** Async-first design enables future solver optimizations
