# Enhanced Combat Summary — Implementation Plan

## Task 1: Save Spec Documentation (IN PROGRESS)

Create `agent-os/specs/2026-01-27-enhanced-combat-summary/` with:

- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context from our conversation)
- **standards.md** — Relevant standards that apply to this work
- **references.md** — Pointers to reference implementations studied
- **visuals/** — Any mockups or screenshots provided (empty)

## Task 2: Add --combat-summary CLI Flag

Add a new boolean flag `--combat-summary` to the `solve_units` command in `src/unicorn_armada/cli.py` to enable detailed combat breakdowns in the summary output.

**Implementation details:**
- Add `combat_summary: Annotated[bool, typer.Option(help="Enable detailed combat breakdown in summary")] = False` parameter to `solve_units()` function
- Default value: `False` (backward compatible)
- Pass this flag through to `write_summary()` call

## Task 3: Create Detailed Combat Summary Function

Create a new function `write_detailed_combat_summary()` in `src/unicorn_armada/cli.py` that:

**Function signature:**
```python
def write_detailed_combat_summary(
    path: Path,
    solution,
    units: list[int],
    combat_scoring: CombatScoringConfig,
) -> None
```

**Implementation details:**
- Takes the solution, unit sizes, combat_scoring config, and output path
- Generates detailed per-unit breakdowns including:
  - Unit number and size
  - List of roles present in each unit (from `CombatUnitBreakdown.roles`)
  - List of capabilities present in each unit (from `CombatUnitBreakdown.capabilities`)
  - Unit combat score (from `CombatUnitBreakdown.score`)
- Appends this information to summary.txt after the basic summary
- Format example:
```
Total rapports: 54
Total combat score: 34.50
Unit 1 (5 slots): 7 rapports, 3.50 combat
berenice, mordon, adel, clive, rolf
Unit 2 (5 slots): 8 rapports, 2.00 combat
virginia, gilbert, berengaria, aramis, travis
...
Unassigned:
bruno, celeste, hilda, leah, ochlys, primm, renault

## Combat Summary Breakdown

Unit 1 (3.50 combat):
  Roles: frontline, support
  Capabilities: archer, cavalry

Unit 2 (2.00 combat):
  Roles: backline, support
  Capabilities: caster, assist
```

## Task 4: Integrate Detailed Summary into write_summary

Modify `write_summary()` to:

**Function signature change:**
```python
def write_summary(
    path: Path,
    solution,
    units: list[int],
    combat_summary: bool = False,
    combat_scoring: CombatScoringConfig | None = None,
) -> None
```

**Implementation details:**
- Add optional `combat_summary` parameter (default `False`)
- Add optional `combat_scoring` parameter (needed for detailed output)
- Write basic summary content as before
- If `combat_summary` is `True` and solution.combat is not None:
  - Call `write_detailed_combat_summary()` with appropriate parameters
- Maintain backward compatibility (default behavior unchanged)

## Task 5: Change Unknown Member Handling to Error

Modify `src/unicorn_armada/combat.py` to raise an error when unknown class members are encountered:

**In `_count_unit_tags()` (lines 19-54):**
- Change unknown member handling from appending to `unknown_members` list to raising an error
- Error message should include which character has unknown class and why
- Example error: `Unknown class for character 'bruno' in roster`

**In `compute_army_coverage()` (lines 72-132):**
- Change unknown member handling from counting to raising an error
- Maintain consistent error behavior across scoring functions

**Error type:** Use `ValueError` or create a custom exception class

## Task 6: Add Tests

Add unit tests for:

**In `tests/unit/test_cli.py` (create if needed):**
- Test `write_detailed_combat_summary()` function
- Test that basic summary still works without flag
- Test that detailed summary appends correctly with flag

**In `tests/unit/test_combat.py`:**
- Test that `_count_unit_tags()` raises error for unknown class members
- Test error message content and clarity
- Update existing tests that rely on graceful unknown member handling

**Integration tests:**
- Test full CLI flow with `--combat-summary` flag
- Verify error is raised when roster has unknown class members

## Task 7: Update Documentation

Update `README.md` to document:

**New CLI flag:**
```
--combat-summary: Enable detailed combat breakdown in summary output (default: false)
```

**Enhanced summary output format:**
- Show example of detailed summary output
- Explain what roles and capabilities mean
- Note that unknown class members will cause an error

**Unknown member behavior:**
- Document that dataset.json should contain complete class data
- Explain that unknown class members will cause the solver to fail
- Provide guidance on how to fix (add character to dataset or character_classes.csv)

**Example:**
```bash
# With detailed combat summary
uv run unicorn-rapport solve-units \
  --units 4,3,4,3 \
  --combat-summary
```

## Definition of Done

- [x] Spec documentation created
- [ ] `--combat-summary` flag added to CLI
- [ ] Detailed combat summary function implemented
- [ ] Summary output appends breakdowns when flag is enabled
- [ ] Unknown class members raise errors instead of being ignored
- [ ] All tests pass
- [ ] README updated with new flag and behavior
- [ ] Backward compatibility maintained (default behavior unchanged)
