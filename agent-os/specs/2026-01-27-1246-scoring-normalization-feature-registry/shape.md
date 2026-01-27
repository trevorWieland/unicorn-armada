# Spec 3: Scoring Normalization Layer + Feature Registry — Shaping Notes

## Scope
Introduce a ClassContext normalization layer and a feature registry for scoring
components (Phase 2 Task Group 2). Normalize class tags/roles once, register
scoring features, and standardize diagnostics for missing data.

## Decisions
- Preserve existing scoring results and output behavior.
- Implement a feature registry with unit + army feature hooks.
- Add diagnostics helpers without changing the JSON output schema.

## Context
- Visuals: None
- References:
  - `src/unicorn_armada/combat.py`
  - `src/unicorn_armada/models.py`
  - `src/unicorn_armada/core.py`
  - `src/unicorn_armada/cli.py`
  - `config/combat_scoring.json`
  - `tests/unit/test_combat.py`
- Product alignment:
  - Rapport stays primary; combat scoring is a tie-breaker/optional filter.
  - Data-driven tags and families (config, not hardcoded).
  - Optional inputs should not break current behavior.

## Standards Applied
- architecture/naming-conventions — consistent names for registry and diagnostics.
- architecture/thin-adapter-pattern — keep CLI thin; core owns scoring logic.
- python/pydantic-only-schemas — new normalization/diagnostics models use Pydantic.
- python/strict-typing-enforcement — explicit types for registry and features.
