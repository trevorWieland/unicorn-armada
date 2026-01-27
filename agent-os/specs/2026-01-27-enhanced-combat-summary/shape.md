# Enhanced Combat Summary — Shaping Notes

## Scope

Add optional detailed combat breakdowns to the summary.txt output via a `--combat-summary` CLI flag. This helps users understand why units receive their combat scores by showing per-unit role and capability breakdowns.

Additionally, change unknown class member handling from graceful degradation to error-raising, since the dataset is expected to be complete.

## Decisions

- Output format: Append detailed breakdowns to existing summary.txt (not separate file)
- Breakdown detail: Basic list of roles/capabilities present per unit (not full weight contributions)
- Unknown members: Raise error instead of handling gracefully (dataset should be complete)
- Backward compatibility: Default behavior unchanged (flag required for detailed output)

## Context

- **Visuals:** None
- **References:**
  - `src/unicorn_armada/cli.py` - Current `write_summary()` function (lines 71-92)
  - `src/unicorn_armada/combat.py` - Combat scoring logic and `_count_unit_tags()` (lines 19-54)
  - `src/unicorn_armada/models.py` - CombatSummary and CombatUnitBreakdown models (lines 368-429)
- **Product alignment:** Phase 1 roadmap item - "Optional summary flag to include per-unit combat breakdowns" and "Expand summary output with breakdown details"

## Standards Applied

- `python/modern-python-314` — Using modern Python 3.14 syntax (T | None, Annotated)
- `python/strict-typing-enforcement` — All functions properly typed with no Any types
- `python/pydantic-only-schemas` — Using Pydantic models for data structures
- `architecture/naming-conventions` — Following snake_case for functions, PascalCase for models
