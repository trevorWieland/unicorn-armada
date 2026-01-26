# Phase 2 Task Plan

Goal: add coverage-aware combat scoring and leader diversity without hard templates, using data-driven weights and neutral fallbacks. Each task-group is independently shippable and can be validated with `uv run ruff check` and `uv run ty check` before moving on.

## Task Group 1: Scoring Data Schema + Defaults
- Add a structured scoring profile (extend `config/combat_scoring.json`) to capture Phase 2 weights:
  - role coverage weights (frontline/support/backline)
  - assist type coverage weights (ranged/magick/healing/none)
  - unit type coverage weights (infantry/cavalry/flying)
  - class type tags (e.g., shield/armor/scout) if desired for later, but optional for now
  - leader diversity weights (per-unit leader class/category diversity)
  - penalties for missing/unknown class data
- Update `CombatScoringConfig` to parse the new fields with defaults.
- Document the new fields in `README.md` (short, data-driven explanation).

Validation:
- `uv run ruff check`
- `uv run ty check`

## Task Group 2: Data Normalization + Feature Hooks
- Add a normalization layer to convert class data into a consistent, scored shape (e.g., `ClassContext`), so scoring features don’t depend on raw schema.
- Implement a feature registry pattern in combat scoring (e.g., `features: list[Callable]`) so Phase 2 scoring adds new features without modifying existing logic.
- Ensure missing class data is treated as neutral (0 contribution), but surfaces warnings for missing defaults when possible.

Validation:
- `uv run ruff check`
- `uv run ty check`

## Task Group 3: Coverage Scoring (Unit-Level)
- Implement unit-level coverage scoring:
  - count roles per unit (frontline/support/backline) and score against weights
  - count assist types per unit (ranged/magick/healing/none) and score against weights
  - count unit types per unit (infantry/cavalry/flying) and score against weights
- Ensure coverage uses soft weights (no hard requirements), so rapport-first solver still works.
- Add coverage details to `CombatSummary` for visibility (optional, but helpful).

Validation:
- `uv run ruff check`
- `uv run ty check`

## Task Group 4: Leader Diversity Scoring (Army-Level)
- Define a “leader class/category” derived from class data (e.g., class id, unit_type, or a configured tag) and compute diversity across units.
- Add a diversity score component (bonus for unique leaders, small penalty for duplicates).
- Allow configuration to tune diversity strength and disable it.

Validation:
- `uv run ruff check`
- `uv run ty check`

## Task Group 5: CLI Surface + Reporting
- Expose Phase 2 controls via CLI (optional flags to tune weights or disable coverage/leader features).
- Update `summary.txt` output to show coverage and diversity totals alongside combat score.
- Update benchmark output (if combat scoring is used) to include the new composite score.

Validation:
- `uv run ruff check`
- `uv run ty check`

## Task Group 6: Calibration + UX Defaults
- Calibrate defaults using `benchmark-units` and real roster samples (no refactor required).
- Set sensible defaults in `config/combat_scoring.json` so a basic run produces meaningful results.
- Add a short guidance section to `README.md` on tuning weights.

Validation:
- `uv run ruff check`
- `uv run ty check`

## Definition of Done
- Rapport solver still works with no new flags.
- Combat scoring includes coverage + leader diversity in the total score.
- Missing class data does not crash scoring; it is neutral with warnings.
- Benchmark and summary output reflect the new scoring components.
