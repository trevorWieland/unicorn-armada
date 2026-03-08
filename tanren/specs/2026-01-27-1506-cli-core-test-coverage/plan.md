# CLI/Core test coverage push — plan

## Goal

Add unit tests for `src/unicorn_armada/cli.py` and `src/unicorn_armada/core.py`, plus BDD-style integration tests, to move toward 80% coverage while following testing standards.

## Tasks

### Task 1: Save spec documentation

- Create `agent-os/specs/2026-01-27-1506-cli-core-test-coverage/` with `plan.md`, `shape.md`, `standards.md`, `references.md`, and an empty `visuals/` directory.

### Task 2: Add CLI unit tests (src/unicorn_armada/cli.py)

- Expand unit coverage for CLI command functions: `solve_units`, `benchmark_units`, `sync_rapports`, and their error handling paths.
- Use unit-tier techniques: mock `run_solve`, `run_benchmark`, `run_sync_rapports`, and I/O where needed.
- Verify parameter wiring, error mapping to `typer.BadParameter`, echo behavior, and file output writes.
- Keep tests under `tests/unit/` consistent with existing `tests/unit/test_cli.py` style.

### Task 3: Add core unit tests (src/unicorn_armada/core.py)

- Cover validation branches in `load_and_validate_problem` (duplicate ids, unknown roster ids, missing units inputs, invalid whitelist/blacklist), plus warning behavior.
- Cover `load_combat_context` branches (missing class warnings, unknown override errors, diagnostics for missing defaults).
- Add tests for `apply_preset` (success + unknown preset error) and `make_combat_score_fn` (None vs callable behavior).
- Cover `run_solve`/`run_benchmark` branches that gate combat scoring, min-combat-score validation, and summary output paths using minimal data and deterministic inputs.

### Task 4: Add BDD-style integration tests (Given/When/Then)

- Create integration scenarios under `tests/integration/` using real `FileStorage` and temp files:
  - Solve flow: Given minimal dataset/roster/units, When running `run_solve`, Then solution + combat summary + warnings/diagnostics behave as expected.
  - CLI solve: Given temp dataset/configs and small trial sizes, When invoking Typer CLI, Then output files + summary contents are correct.
  - Sync rapports: Given dataset with missing reciprocal pairs, When running sync, Then output dataset/report reflect changes.
- Use explicit Given/When/Then sections (fixture names or comments) to satisfy BDD standard without adding new dependencies.

### Task 5: Verify coverage and thresholds

- Run unit + integration tiers and coverage to confirm movement toward 80%.
- If coverage reaches target, update `fail_under` to 80; otherwise report remaining gaps and propose next coverage targets.

## References

- `src/unicorn_armada/cli.py`
- `src/unicorn_armada/core.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_core.py`
- `tests/integration/conftest.py`

## Standards to apply

- `testing/three-tier-test-structure`
- `testing/bdd-for-integration-quality`
- `testing/mandatory-coverage`
- `testing/no-test-skipping`
- `testing/test-timing-rules`
- `testing/no-mocks-for-quality-tests` (no quality tests planned)
