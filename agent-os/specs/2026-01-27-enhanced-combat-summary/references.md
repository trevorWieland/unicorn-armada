# References for Enhanced Combat Summary

## Similar Implementations

### Current Summary Output (write_summary)

- **Location:** `src/unicorn_armada/cli.py` (lines 71-92)
- **Relevance:** Shows current summary format and structure
- **Key patterns:**
  - Uses Path object for file writing
  - Builds lines list then joins with newline
  - Appends newline at end
  - Iterates through solution.units and solution.unit_rapports

```python
def write_summary(path: Path, solution, units: list[int]) -> None:
    lines = [f"Total rapports: {solution.total_rapports}"]
    if solution.combat is not None:
        lines.append(f"Total combat score: {solution.combat.total_score:.2f}")
    for idx, (unit, score) in enumerate(
        zip(solution.units, solution.unit_rapports, strict=False), start=1
    ):
        combat_score = None
        if solution.combat is not None and idx - 1 < len(solution.combat.unit_scores):
            combat_score = solution.combat.unit_scores[idx - 1]
        if combat_score is None:
            lines.append(f"Unit {idx} ({units[idx - 1]} slots): {score} rapports")
        else:
            lines.append(
                f"Unit {idx} ({units[idx - 1]} slots): {score} rapports, "
                f"{combat_score:.2f} combat"
            )
        lines.append(", ".join(unit) if unit else "(empty)")
    if solution.unassigned:
        lines.append("Unassigned:")
        lines.append(", ".join(solution.unassigned))
    path.write_text("\n".join(lines) + "\n")
```

### Combat Unit Breakdown Data Model

- **Location:** `src/unicorn_armada/models.py` (lines 368-380)
- **Relevance:** Contains the data structure for unit breakdowns that will be used in detailed summary
- **Key fields:**
  - `roles: dict[str, int]` - Count of each role in the unit
  - `capabilities: dict[str, int]` - Count of each capability in the unit
  - `unknown_members: list[str]` - Members with unknown class data
  - `score: float` - Combat score for this unit

```python
class CombatUnitBreakdown(BaseModel):
    """Breakdown of combat scoring for a single unit."""

    roles: dict[str, int] = Field(
        default_factory=dict, description="Count of each role in the unit"
    )
    capabilities: dict[str, int] = Field(
        default_factory=dict, description="Count of each capability in the unit"
    )
    unknown_members: list[str] = Field(
        default_factory=list, description="Members with unknown class data"
    )
    score: float = Field(0.0, description="Combat score for this unit")
```

### Combat Summary Data Model

- **Location:** `src/unicorn_armada/models.py` (lines 409-428)
- **Relevance:** Contains unit_breakdowns list that will be used for detailed output
- **Key fields:**
  - `unit_breakdowns: list[CombatUnitBreakdown]` - Detailed breakdown per unit

```python
class CombatSummary(BaseModel):
    """Complete combat summary for a solution."""

    unit_scores: list[float] = Field(
        default_factory=list, description="Combat score per unit"
    )
    unit_breakdowns: list[CombatUnitBreakdown] = Field(
        default_factory=list, description="Detailed breakdown per unit"
    )
    total_score: float = Field(0.0, description="Sum of unit combat scores")
    coverage: CoverageSummary = Field(
        default_factory=CoverageSummary, description="Army coverage summary"
    )
    diversity: DiversitySummary = Field(
        default_factory=DiversitySummary, description="Leader diversity summary"
    )

    @property
    def army_total_score(self) -> float:
        return self.total_score + self.coverage.total_score + self.diversity.score
```

### Current Unknown Member Handling

- **Location:** `src/unicorn_armada/combat.py` (lines 19-54, 72-132)
- **Relevance:** Shows current graceful handling that will be changed to error-raising
- **Key patterns:**
  - In `_count_unit_tags()`: Appends unknown members to list, continues processing
  - In `compute_army_coverage()`: Counts unknown members, passes silently
  - This will be changed to raise `ValueError` with descriptive message

```python
def _count_unit_tags(
    unit: list[str],
    character_classes: dict[str, str],
    class_index: dict[str, ClassDefinition],
) -> tuple[dict[str, int], dict[str, int], list[str]]:
    roles: dict[str, int] = {}
    capabilities: dict[str, int] = {}
    unknown_members: list[str] = []

    for member in unit:
        class_id = character_classes.get(member)
        if not class_id:
            unknown_members.append(member)  # CHANGE THIS: raise ValueError instead
            continue
        class_family = class_index.get(class_id)
        if class_family is None:
            unknown_members.append(member)  # CHANGE THIS: raise ValueError instead
            continue
        # ... rest of processing
```

### CLI Flag Patterns

- **Location:** `src/unicorn_armada/cli.py` (lines 414-457)
- **Relevance:** Shows how boolean flags are implemented in Typer
- **Key patterns:**
  - Use `Annotated[bool, typer.Option(help="...")]` for boolean flags
  - Default to `False` for optional features
  - Pass flag values through function calls

```python
@app.command()
def solve_units(
    dataset: Annotated[
        Path | None,
        typer.Option(help="Path to dataset JSON (default: data/dataset.json)"),
    ] = None,
    # ... other parameters
    summary: Annotated[Path, typer.Option(help="Summary output path")] = Path(
        "out/summary.txt"
    ),
) -> None:
    # ... implementation
```

### Test Patterns for CLI Functions

- **Location:** `tests/unit/` (various test files)
- **Relevance:** Shows patterns for testing CLI functions and error handling
- **Key patterns:**
  - Use pytest fixtures for common test data
  - Use `pytest.raises` for testing error conditions
  - Test both success and failure cases
  - Use temporary files for file I/O testing
