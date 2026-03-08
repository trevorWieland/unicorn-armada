# CLI/Core test coverage push — Shaping Notes

## Scope

- Add unit tests for `src/unicorn_armada/cli.py` and `src/unicorn_armada/core.py`.
- Add BDD-style integration tests (Given/When/Then) under `tests/integration/`.
- Move overall coverage toward 80%; update `fail_under` only if target is met.

## Decisions

- No new testing dependencies; use pytest with explicit Given/When/Then sections.
- Integration tests use real `FileStorage` with temp files.
- Unit tests mock external behaviors and validate parameter wiring and error mapping.

## Context

- **Visuals:** None
- **References:** `src/unicorn_armada/cli.py`, `src/unicorn_armada/core.py`, `tests/unit/test_cli.py`, `tests/unit/test_core.py`, `tests/integration/conftest.py`
- **Product alignment:** Aligns with Phase 2 testing standards (CLI/core unit tests, BDD integration tests, target 80% coverage)

## Standards Applied

- `testing/three-tier-test-structure` — keep tests under unit/integration/quality tiers.
- `testing/bdd-for-integration-quality` — Given/When/Then structure for integration tests.
- `testing/mandatory-coverage` — behavior-focused tests that cover branches and errors.
- `testing/no-test-skipping` — do not skip tests.
- `testing/test-timing-rules` — keep tests within tier time bounds.
- `testing/no-mocks-for-quality-tests` — no quality tests planned.
