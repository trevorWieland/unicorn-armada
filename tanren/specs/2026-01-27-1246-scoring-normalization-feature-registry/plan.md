# Spec 3: Scoring Normalization Layer + Feature Registry

## Goal
Introduce a ClassContext normalization layer and a feature registry for scoring
components (Phase 2 Task Group 2).

## Value
Make scoring extensible and consistent so future features (role coverage,
class-type tags) can plug in cleanly.

## Success Criteria
- Existing scoring results are preserved.
- Adding a new scoring feature requires only registry registration + config.
- Diagnostics for missing data are standardized.

## Plan

### Task 1: Save Spec Documentation
Create `agent-os/specs/2026-01-27-1246-scoring-normalization-feature-registry/` with:
- `plan.md` — full plan
- `shape.md` — scope + decisions + context
- `standards.md` — standards content
- `references.md` — code references
- `visuals/` — empty (none provided)

### Task 2: Define normalization + diagnostics models
- Add Pydantic models for `ClassContext` (normalized/derived tags) and
  `CombatDiagnostic` (code, severity, message, subject).
- Implement a `ClassContext` builder and index helper to normalize roles,
  capabilities, class types, and derived tags once per class.

### Task 3: Add feature registry for scoring components
- Define strict-typed unit and army feature protocols.
- Implement a `FeatureRegistry` that registers features and runs them in a
  deterministic order.
- Register existing features:
  - Unit tag scoring (roles/capabilities)
  - Army coverage (assist types + unit types)
  - Leader diversity

### Task 4: Refactor combat scoring to use normalization + registry
- Replace `_count_unit_tags` / `_score_unit_tags` internals with normalization
  output + registry-driven scoring.
- Update `compute_combat_summary` to:
  - Build ClassContext index once
  - Compute per-unit breakdowns via registry
  - Compute coverage/diversity via registry
  - Preserve score totals exactly

### Task 5: Surface standardized diagnostics
- Define diagnostic codes for missing class mapping, unknown class id, and
  missing default classes.
- Use diagnostics to format warnings and error messages consistently.

### Task 6: Update tests to lock behavior
- Add targeted tests for derived-tag normalization and diagnostic formatting.
- Ensure existing scoring tests still pass and totals are unchanged.
