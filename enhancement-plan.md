# Enhancement Plan: Combat Weighting + Team Composition

Temporary working doc for the combat-scoring enhancement. Remove when complete.

## Principles

- Rapport stays primary; combat score is tie-breaker and optional filter.
- Data-driven: class families and tags live in config files.
- Family-only class stage by default (promotions do not change core role).
- Soft scoring, no hard comp templates.
- Optional inputs; missing data must not break current behavior.

## Phase 0: Groundwork (No Behavior Change)

Goal: add metadata and scoring plumbing without affecting solver outcomes.

Deliverables:
- Dataset schemas (game truth in `data/dataset.json`):
  - `classes` (class details + role tags, capabilities, row preference).
  - `class_lines` (valid class options per line).
  - `character_classes` (default class + class line per character).
- User config:
  - `config/character_classes.csv` (override current class).
  - `config/combat_scoring.json` (weights; defaults to zero).
- Models + validation for the above files.
- Optional loading of class data; missing data yields "unknown" class/role.
- Compute `combat_score` + `combat_breakdown` per unit, but do not use in solver.
- Extend output JSON to include combat fields with zero defaults when disabled.
- README updates documenting optional inputs and output fields.
- Tests to confirm no behavior change when configs are absent.

Out of scope:
- Any solver tie-breaking by combat score.
- Min combat score filtering.
- Leader diversity.
- Army-level coverage targets.
- Formation row/grid scoring.

## Phase 1: Unit-Level Combat Tie-Breaker

Goal: use combat scoring to improve team utility while preserving rapport priority.

Deliverables:
- Lexicographic objective: maximize rapport, then combat score.
- `--min-combat-score` filter to drop solutions below a threshold.
- Sensible default weights for role balance + capability presence.
- Per-unit combat breakdown in summary output (optional flag).

Out of scope:
- Leader diversity across units.
- Army-level coverage targets.
- Formation grid/row assignment.

## Phase 2: Army Coverage + Leader Diversity

Goal: encourage overall strategic coverage and avoid leader redundancy.

Deliverables:
- Army-level coverage scoring (assist/cavalry/flying, etc.) scaled by unit count.
- Leader selection heuristic (best leader per unit by class tags).
- Penalty for repeating leader class across units; still soft.
- Optional class-stage override for capability tags (family-only default).

Out of scope:
- Formation grid/row optimization.

## Phase 3: Formation-Aware Scoring + Benchmarks

Goal: incorporate front/back row preferences without rigid templates.

Deliverables:
- Optional 2x3 grid or row placement per unit.
- Row-fit scoring (front/back/flex) with soft penalties.
- Lightweight benchmark comps (good/bad) for scoring sanity checks only.
- Output includes row assignments and row-fit score components.

Out of scope:
- Full battle sim or enemy-specific optimization.

## Beyond Phase 3 (Future)

- Skill-level tags and conditional effects (anti-air, cleanse, guard, etc.).
- Enemy composition-aware weighting.
- Equipment/tactics modeling.
- Simulation-based evaluation pass.
