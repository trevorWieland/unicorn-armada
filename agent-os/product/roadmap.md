# Product Roadmap

Living document that captures shipped capabilities and planned work. Checkboxes
reflect current status.

## Legend
- [x] Done
- [ ] Planned

---

## Design Principles

Core principles guiding combat scoring and team composition enhancements:

- **Rapport stays primary** — Combat score is tie-breaker and optional filter only.
- **Data-driven** — Class families and tags live in config files, not hardcoded.
- **Family-only class stage** — Promotions do not change core role by default.
- **Soft scoring** — No hard comp templates; use weighted preferences.
- **Optional inputs** — Missing data must not break current behavior.

---

## Standards Alignment Work

### Phase 1: Code Quality Standards Alignment (COMPLETE)
**Date:** 2026-01-27
**Scope:** Align codebase with 11 Agent OS standards (Architecture, Global, Python)

#### Completed
- [x] Python 3.14 upgrade with modern syntax (`T | None`, `Annotated`)
- [x] Converted all dataclasses to Pydantic BaseModel with Field descriptions
- [x] Strict typing enforcement (removed `object`/`Any` types)
- [x] Fixed naming inconsistencies (`assist_type` vs `assistance`)
- [x] Thin adapter pattern - extracted business logic to `core.py`
- [x] Protocol interfaces for IO/storage (`protocols.py`)
- [x] API response envelope (`responses.py`) with `{data, error, meta}` structure
- [x] Structured JSONL logging infrastructure (`logging.py`)
- [x] Deprecation enforcement configured in ruff/pytest
- [x] Non-pinned dependency ranges with `uv.lock` for reproducibility
- [x] Async-first design deferred (N/A - no network I/O in codebase)

#### New Files Created
- `src/unicorn_armada/core.py` - Core business logic extracted from CLI
- `src/unicorn_armada/protocols.py` - Protocol interfaces for dependency injection
- `src/unicorn_armada/responses.py` - API response envelope models
- `src/unicorn_armada/logging.py` - Structured JSONL logging

#### Standards Applied
- `architecture/adapter-interface-protocol`
- `architecture/api-response-format`
- `architecture/log-line-format`
- `architecture/naming-conventions`
- `architecture/thin-adapter-pattern`
- `global/address-deprecations-immediately`
- `global/prefer-dependency-updates`
- `python/async-first-design` (deferred)
- `python/modern-python-314`
- `python/pydantic-only-schemas`
- `python/strict-typing-enforcement`

### Phase 2: Testing Standards Alignment (IN PROGRESS)
**Date:** 2026-01-27
**Scope:** Implement testing infrastructure with 6 Agent OS testing standards

#### Completed
- [x] Makefile with common commands (format, lint, type, unit, integration, quality)
- [x] pytest + testing dependencies added to pyproject.toml
- [x] Three-tier test structure created (`tests/unit/`, `tests/integration/`, `tests/quality/`)
- [x] pytest markers configured (unit, integration, quality)
- [x] Timing rules configured via pytest-timeout (1s/5s/30s)
- [x] Coverage thresholds configured (35% initial, target 80%)
- [x] Unit tests for `utils.py` (15 tests, 100% coverage)
- [x] Unit tests for `models.py` (23 tests, 79% coverage)
- [x] Unit tests for `io.py` (25 tests, 80% coverage)
- [x] Unit tests for `scoring.py` (9 tests, 100% coverage)
- [x] Unit tests for `solver.py` (19 tests, 75% coverage)
- [x] Unit tests for `combat.py` (52 tests)
- [x] Unit tests for `benchmark.py` (37 tests)

#### Remaining
- [ ] Unit tests for `cli.py` (command tests)
- [ ] Unit tests for `core.py`
- [ ] Integration tests with BDD style (Given/When/Then)
- [ ] Quality tests (if applicable - no LLM usage in this codebase)
- [ ] Raise coverage threshold to 80%
- [ ] Phase 2 spec documentation

#### Current Metrics
- **180 unit tests** passing
- **52% total coverage** (target 80%)
- All `make all` checks pass (format, lint, type, unit)

#### Standards Being Applied
- `testing/three-tier-test-structure`
- `testing/bdd-for-integration-quality`
- `testing/mandatory-coverage`
- `testing/no-mocks-for-quality-tests`
- `testing/no-test-skipping`
- `testing/test-timing-rules`

---

## Audit Snapshot (Current Capabilities)

### Repo and Tooling
- [x] Repo scaffold with `src/` layout and `pyproject.toml`.
- [x] Package metadata and versioning (`unicorn-armada`).
- [x] CLI entrypoint `unicorn-rapport` and module `__main__`.
- [x] Python 3.14 with modern type syntax.
- [x] Ruff linting with comprehensive rule set.
- [x] ty type checking configured.
- [x] Makefile for common development commands.

### CLI and UX
- [x] `solve-units` command with dataset/roster/units/whitelist/blacklist inputs.
- [x] `benchmark-units` command for combat score baselines.
- [x] `sync-rapports` command to normalize rapport pairs.
- [x] Deterministic runs with seed, restarts, and swap iterations.
- [x] Units can be provided via `--units` or `--units-file`.
- [x] Modern Typer Annotated syntax for CLI options.

### Data and Inputs
- [x] Dataset schema for characters, rapports, classes, class lines, and character classes.
- [x] Pydantic validation and normalization of ids/tags.
- [x] CSV loaders for roster, whitelist/blacklist, and class overrides.
- [x] Combat scoring config loader with defaults.
- [x] Local config/data folders with sample files.
- [x] Protocol interfaces for storage abstraction.

### Solver and Optimization
- [x] Whitelist clustering via union-find.
- [x] Blacklist conflict detection.
- [x] Greedy initial assignment with restarts.
- [x] Swap-based local improvement.
- [x] Roster trimming to fit unit slots (drop least promising clusters).
- [x] Dummy slots for undersized rosters.
- [x] Rapport-first optimization with combat tie-breaker.
- [x] Optional minimum combat score filter.

### Combat and Army Scoring
- [x] Unit role/capability scoring using class tags.
- [x] Unit breakdowns with unknown member handling.
- [x] Army coverage scoring (assist types and unit types).
- [x] Leader selection heuristic (leader effect > class data > fallback).
- [x] Leader diversity scoring with configurable modes.
- [x] Preset profiles (balanced, offensive, defensive, magic-heavy).

### Reporting and Outputs
- [x] `out/solution.json` with combat summary fields.
- [x] `out/summary.txt` with rapport and combat per unit.
- [x] Benchmark outputs with percentiles and recommendations.
- [x] README documentation for inputs, outputs, flags, and scoring.
- [x] API response envelope for JSON outputs.

### Data Reference
- [x] Class reference catalog in `CLASS_REFERENCE.md`.

---

## Roadmap (Detailed)

### Phase 0: Groundwork (Data/Scoring Plumbing)
- [x] Dataset schemas for classes, class lines, and character classes.
- [x] Config inputs for class overrides and combat scoring weights.
- [x] Data models and validation for new schemas.
- [x] Optional loading of class data with neutral fallback.
- [x] Per-unit combat scoring computed and emitted in output JSON.
- [x] README updates documenting optional inputs and outputs.
- [ ] Tests to confirm no behavior change when configs are absent.

### Phase 1: Unit-Level Combat Tie-Breaker (COMPLETE)
- [x] Lexicographic objective: maximize rapports, then combat score.
- [x] `--min-combat-score` filter.
- [x] Default role/capability weights and presets.
- [x] Optional summary flag to include per-unit combat breakdowns.
- [x] Expand summary output with breakdown details (roles/capabilities/unknowns).

**Completed:** 2026-01-27
**Details:** Added `--combat-summary` CLI flag with detailed per-unit breakdowns showing roles and capabilities. Changed unknown class member handling from graceful degradation to error-raising.

### Phase 2: Army Coverage and Leader Diversity

#### Task Group 1: Scoring Data Schema and Defaults
- [x] Coverage weights for assist types.
- [x] Coverage weights for unit types.
- [x] Diversity weights with configurable mode.
- [ ] Role coverage weights (frontline/support/backline).
- [x] Error-raising for missing or unknown class data (enforces complete dataset).
- [ ] Optional class-type tags for future scoring.

#### Task Group 2: Data Normalization and Feature Hooks
- [ ] Normalization layer (e.g., ClassContext) for scored attributes.
- [ ] Feature registry pattern for scoring components.
- [x] Warnings for missing default classes in roster.
- [ ] Standardized diagnostics surfaced to users.

#### Task Group 3: Coverage Scoring (Unit-Level)
- [ ] Unit-level coverage scoring by roles/assist types/unit types.
- [x] Army-level coverage scoring for assist and unit types (current behavior).
- [ ] Coverage breakdowns in summary output.

#### Task Group 4: Leader Diversity Scoring (Army-Level)
- [x] Leader selection heuristic.
- [x] Diversity score with unique bonus and duplicate penalty.
- [ ] Align `assist_type` diversity mode handling end-to-end.

#### Task Group 5: CLI Surface and Reporting
- [x] CLI flags to enable/disable coverage and diversity.
- [x] CLI flag for diversity mode.
- [x] Summary output includes coverage and diversity totals.
- [x] Benchmark output uses army total score.
- [ ] CLI flags to tune scoring weights directly.
- [ ] Richer coverage/diversity breakdowns in outputs.

#### Task Group 6: Calibration and UX Defaults
- [ ] Calibrate default weights using benchmark runs and real rosters.
- [ ] Guidance in README for tuning and interpreting scores.

#### Definition of Done (Phase 2)
- Rapport solver still works with no new flags.
- Combat scoring includes coverage + leader diversity in the total score.
- Missing class data raises errors; dataset must be complete for all roster characters.
- Benchmark and summary output reflect the new scoring components.

### Phase 3: Formation-Aware Scoring and Benchmarks
- [ ] Optional 2x3 grid or row placement per unit.
- [ ] Row-fit scoring using front/back/flex preferences.
- [ ] Lightweight benchmark comps for scoring sanity checks.
- [ ] Output row assignments and row-fit breakdowns.

### Beyond Phase 3 (Future)
- [ ] Skill-level tags and conditional effects.
- [ ] Equipment and tactics modeling.
- [ ] AP/PP modeling.
- [ ] Build recommendations alongside compositions.
- [ ] Enemy composition-aware weighting.
- [ ] Simulation-based evaluation pass.

---

## Product and UX Direction
- [ ] Textual TUI for roster/config input and composition review.
- [ ] Export and share formats (JSON, text, optional CSV).
- [ ] Preset management UX and custom preset definitions.

---

## Engineering and Tooling

### Completed
- [x] Python 3.14 upgrade with modern type syntax.
- [x] Ruff linting with deprecation detection (pyupgrade rules).
- [x] ty type checking configured.
- [x] Makefile with format/lint/type/test commands.
- [x] pytest infrastructure with three-tier test structure.
- [x] Coverage reporting configured.
- [x] Protocol interfaces for testability.
- [x] API response envelope standardization.
- [x] Structured logging infrastructure.

### Remaining
- [ ] Raise test coverage to 80% threshold.
- [ ] Add CI pipeline (GitHub Actions or similar).
- [ ] Switch build system from setuptools to uv-native workflow.
- [ ] Add pre-commit hooks for format/lint.

---

## Future Enhancements (Post-Standards Alignment)

### Code Quality
- [x] Extract all relevant business logic from CLI to core.py to adhere to standards.
- [x] Add FileStorage usage in CLI (currently uses direct functions)
- [ ] Implement structured logging in CLI commands
- [ ] Add API response envelope to all JSON outputs (currently only benchmark)

### Testing
- [ ] Add property-based testing with Hypothesis
- [ ] Add mutation testing to verify test quality
- [ ] Add benchmark tests for solver performance regression
- [ ] Add snapshot tests for output format stability

### Architecture
- [ ] Consider async-first posture.
- [ ] Add plugin system for custom scoring strategies
- [ ] Add configuration file support (TOML/YAML) for complex setups

### Documentation
- [ ] Add contributing guide for agent-os usage.
- [ ] Add developer guide for extending the solver
- [ ] Add API documentation for core module

### CI/CD
- [ ] GitHub Actions workflow for PR checks
- [ ] Automated releases with changelog generation
- [ ] Dependency update automation (Dependabot or Renovate)
