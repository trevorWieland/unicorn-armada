# Product Roadmap

Living document that captures shipped capabilities and planned work. Checkboxes
reflect current status.

## Legend
- [x] Done
- [ ] Planned

## Audit Snapshot (Current Capabilities)
### Repo and Tooling
- [x] Repo scaffold with `src/` layout and `pyproject.toml`.
- [x] Package metadata and versioning (`unicorn-armada`).
- [x] CLI entrypoint `unicorn-rapport` and module `__main__`.

### CLI and UX
- [x] `solve-units` command with dataset/roster/units/whitelist/blacklist inputs.
- [x] `benchmark-units` command for combat score baselines.
- [x] `sync-rapports` command to normalize rapport pairs.
- [x] Deterministic runs with seed, restarts, and swap iterations.
- [x] Units can be provided via `--units` or `--units-file`.

### Data and Inputs
- [x] Dataset schema for characters, rapports, classes, class lines, and character classes.
- [x] Pydantic validation and normalization of ids/tags.
- [x] CSV loaders for roster, whitelist/blacklist, and class overrides.
- [x] Combat scoring config loader with defaults.
- [x] Local config/data folders with sample files.

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

### Data Reference
- [x] Class reference catalog in `CLASS_REFERENCE.md`.

## Roadmap (Detailed)
### Phase 0: Groundwork (Data/Scoring Plumbing)
- [x] Dataset schemas for classes, class lines, and character classes.
- [x] Config inputs for class overrides and combat scoring weights.
- [x] Data models and validation for new schemas.
- [x] Optional loading of class data with neutral fallback.
- [x] Per-unit combat scoring computed and emitted in output JSON.
- [x] README updates documenting optional inputs and outputs.
- [ ] Tests to confirm no behavior change when configs are absent.

### Phase 1: Unit-Level Combat Tie-Breaker
- [x] Lexicographic objective: maximize rapports, then combat score.
- [x] `--min-combat-score` filter.
- [x] Default role/capability weights and presets.
- [ ] Optional summary flag to include per-unit combat breakdowns.
- [ ] Expand summary output with breakdown details (roles/capabilities/unknowns).

### Phase 2: Army Coverage and Leader Diversity
#### Task Group 1: Scoring Data Schema and Defaults
- [x] Coverage weights for assist types.
- [x] Coverage weights for unit types.
- [x] Diversity weights with configurable mode.
- [ ] Role coverage weights (frontline/support/backline).
- [ ] Penalty weights for missing or unknown class data.
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

## Product and UX Direction
- [ ] Textual TUI for roster/config input and composition review.
- [ ] Export and share formats (JSON, text, optional CSV).
- [ ] Preset management UX and custom preset definitions.

## Engineering and Tooling
- [ ] Audit alignment (remediate gaps in REPO_AUDIT.md).
- [ ] Switch build system from setuptools to uv build workflow.
- [ ] Add automated tests for solver, IO validation, and combat scoring.
- [ ] Add CI checks for linting and typing (ruff, ty).
