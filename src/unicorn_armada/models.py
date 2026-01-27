from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .utils import normalize_tag


def _normalize_tags(value: list[str] | None, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in value:
        item_str = normalize_tag(str(item))
        if not item_str or item_str in seen:
            continue
        seen.add(item_str)
        cleaned.append(item_str)
    return cleaned


def _normalize_weights(
    value: dict[str, float] | None, field_name: str
) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    cleaned: dict[str, float] = {}
    for key, weight in value.items():
        key_str = normalize_tag(str(key))
        if not key_str:
            continue
        cleaned[key_str] = float(weight)
    return cleaned


def _normalize_identifier(value: str, field_name: str) -> str:
    cleaned = normalize_tag(str(value))
    if " " in cleaned:
        raise ValueError(f"{field_name} must use underscores instead of spaces")
    return cleaned


DiagnosticSeverity = Literal["warning", "error"]
DiagnosticCode = Literal[
    "missing_class_mapping",
    "unknown_class_id",
    "missing_default_classes",
]


class Character(BaseModel):
    """A game character."""

    id: Annotated[str, Field(min_length=1, description="Unique character identifier")]
    name: str | None = Field(None, description="Display name of the character")

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return value.strip()


class RapportListEntry(BaseModel):
    """Rapport pairs for a single character."""

    id: Annotated[str, Field(min_length=1, description="Character identifier")]
    pairs: list[str] = Field(
        default_factory=list,
        description="List of character IDs this character has rapport with",
    )

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return value.strip()

    @field_validator("pairs", mode="before")
    @classmethod
    def normalize_pairs(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("pairs must be a list")
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value:
            item_str = str(item).strip()
            if not item_str or item_str in seen:
                continue
            seen.add(item_str)
            cleaned.append(item_str)
        return cleaned

    @model_validator(mode="after")
    def validate_pairs(self) -> RapportListEntry:
        if self.id in self.pairs:
            raise ValueError("Rapport list cannot include self in pairs")
        return self


class Dataset(BaseModel):
    """Complete game dataset with characters, rapports, and class definitions."""

    characters: list[Character] = Field(..., description="List of all characters")
    rapports: list[RapportListEntry] = Field(
        ..., description="Rapport pair data for characters"
    )
    classes: list[ClassDefinition] = Field(
        default_factory=list, description="Class definitions with roles and stats"
    )
    class_lines: list[ClassLine] = Field(
        default_factory=list, description="Class promotion lines"
    )
    character_classes: dict[str, CharacterClassInfo] = Field(
        default_factory=dict, description="Default class assignments per character"
    )

    @model_validator(mode="after")
    def validate_class_references(self) -> Dataset:
        class_ids = {entry.id for entry in self.classes}
        if len(class_ids) != len(self.classes):
            raise ValueError("Class definitions contain duplicate ids")

        line_ids = [line.id for line in self.class_lines]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("Class lines contain duplicate ids")

        line_index = {line.id: line for line in self.class_lines}
        for line in self.class_lines:
            for class_id in line.classes:
                if class_id not in class_ids:
                    raise ValueError(
                        f"Class line {line.id} references unknown class: {class_id}"
                    )

        character_ids = {character.id for character in self.characters}
        for character_id in self.character_classes:
            if character_id not in character_ids:
                raise ValueError(
                    f"Character classes contain unknown character id: {character_id}"
                )

        for character_id, info in self.character_classes.items():
            if info.default_class not in class_ids:
                raise ValueError(
                    f"Character {character_id} references unknown class: "
                    f"{info.default_class}"
                )
            if info.class_line is None:
                continue
            line = line_index.get(info.class_line)
            if line is None:
                raise ValueError(
                    f"Character {character_id} references unknown class line: "
                    f"{info.class_line}"
                )
            if info.default_class not in line.classes:
                raise ValueError(
                    f"Character {character_id} default class {info.default_class} "
                    f"is not part of class line {info.class_line}"
                )
        return self


class LeaderEffect(BaseModel):
    """Special effect when a character is the unit leader."""

    name: Annotated[str, Field(min_length=1, description="Effect name")]
    description: Annotated[str, Field(min_length=1, description="Effect description")]


class ClassDefinition(BaseModel):
    """Definition of a character class with stats and capabilities."""

    id: Annotated[str, Field(min_length=1, description="Unique class identifier")]
    name: str | None = Field(None, description="Display name of the class")
    roles: list[str] = Field(..., description="Combat roles (e.g., tank, dps, support)")
    capabilities: list[str] = Field(
        default_factory=list, description="Special capabilities of this class"
    )
    row_preference: Literal["front", "back", "flex"] = Field(
        "flex", description="Preferred row position in formation"
    )
    class_types: list[str] = Field(..., description="Class type tags")
    unit_type: Literal["infantry", "cavalry", "flying"] = Field(
        ..., description="Movement and unit type category"
    )
    assist_type: Literal["none", "ranged", "magick", "healing"] = Field(
        ..., description="Type of assist attacks this class provides"
    )
    leader_effect: LeaderEffect | None = Field(
        None, description="Special effect when leading a unit"
    )
    class_trait: str | None = Field(None, description="Unique class trait")
    stamina: int = Field(..., description="Base stamina stat")
    mobility: int = Field(..., description="Base mobility stat")
    promotes_to: str | None = Field(None, description="Class this promotes to")

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return _normalize_identifier(str(value), "class id")

    @field_validator("roles", mode="before")
    @classmethod
    def normalize_roles(cls, value: list[str] | None) -> list[str]:
        roles = _normalize_tags(value, "roles")
        if not roles:
            raise ValueError("roles must contain at least one entry")
        return roles

    @field_validator("capabilities", mode="before")
    @classmethod
    def normalize_capabilities(cls, value: list[str] | None) -> list[str]:
        return _normalize_tags(value, "capabilities")

    @field_validator("row_preference", mode="before")
    @classmethod
    def normalize_row_preference(cls, value: str | None) -> str:
        if value is None:
            return "flex"
        return normalize_tag(str(value))

    @field_validator("class_types", mode="before")
    @classmethod
    def normalize_class_types(cls, value: list[str] | None) -> list[str]:
        class_types = _normalize_tags(value, "class_types")
        if not class_types:
            raise ValueError("class_types must contain at least one entry")
        return class_types

    @field_validator("unit_type", mode="before")
    @classmethod
    def normalize_unit_type(cls, value: str) -> str:
        return normalize_tag(str(value))

    @field_validator("assist_type", mode="before")
    @classmethod
    def normalize_assist_type(cls, value: str) -> str:
        return normalize_tag(str(value))

    @field_validator("promotes_to", mode="before")
    @classmethod
    def normalize_promotes_to(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_identifier(str(value), "promotes_to")


class ClassContext(BaseModel):
    """Normalized class context for scoring."""

    class_id: Annotated[str, Field(min_length=1, description="Class identifier")]
    roles: list[str] = Field(default_factory=list, description="Normalized role tags")
    capabilities: list[str] = Field(
        default_factory=list, description="Normalized capability tags"
    )
    class_types: list[str] = Field(
        default_factory=list, description="Normalized class type tags"
    )
    unit_type: Literal["infantry", "cavalry", "flying"] = Field(
        ..., description="Movement and unit type category"
    )
    assist_type: Literal["none", "ranged", "magick", "healing"] = Field(
        ..., description="Type of assist attacks this class provides"
    )
    has_leader_effect: bool = Field(
        False, description="Whether class has a leader effect"
    )


class ClassLine(BaseModel):
    """A promotion line of related classes."""

    id: Annotated[str, Field(min_length=1, description="Unique class line identifier")]
    name: str | None = Field(None, description="Display name for the class line")
    classes: list[str] = Field(..., description="Class IDs in this promotion line")

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return _normalize_identifier(str(value), "class line id")

    @field_validator("classes", mode="before")
    @classmethod
    def normalize_classes(cls, value: list[str] | None) -> list[str]:
        class_ids = _normalize_tags(value, "classes")
        if not class_ids:
            raise ValueError("classes must contain at least one entry")
        for class_id in class_ids:
            if " " in class_id:
                raise ValueError(
                    "class line entries must use underscores instead of spaces"
                )
        return class_ids


class CharacterClassInfo(BaseModel):
    """Class assignment info for a character."""

    default_class: Annotated[
        str, Field(min_length=1, description="Default class for this character")
    ]
    class_line: str | None = Field(
        None, description="Class line this character belongs to"
    )

    @field_validator("default_class", mode="before")
    @classmethod
    def normalize_default_class(cls, value: str) -> str:
        return _normalize_identifier(str(value), "default_class")

    @field_validator("class_line", mode="before")
    @classmethod
    def normalize_class_line(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_identifier(str(value), "class_line")


class CoverageWeights(BaseModel):
    """Weights for army coverage scoring."""

    enabled: bool = Field(True, description="Whether coverage scoring is enabled")
    assist_type_weights: dict[str, float] = Field(
        default_factory=lambda: {"ranged": 0.5, "magick": 0.5, "healing": 0.5},
        description="Weights for assist type coverage",
    )
    unit_type_weights: dict[str, float] = Field(
        default_factory=lambda: {"infantry": 0.3, "cavalry": 0.3, "flying": 0.3},
        description="Weights for unit type coverage",
    )
    target_multiplier: float = Field(1.0, description="Multiplier for target coverage")

    @field_validator("assist_type_weights", mode="before")
    @classmethod
    def normalize_assist_type_weights(
        cls, value: dict[str, float] | None
    ) -> dict[str, float]:
        return _normalize_weights(value, "assist_type_weights")

    @field_validator("unit_type_weights", mode="before")
    @classmethod
    def normalize_unit_type_weights(
        cls, value: dict[str, float] | None
    ) -> dict[str, float]:
        return _normalize_weights(value, "unit_type_weights")


class DiversityWeights(BaseModel):
    """Weights for leader diversity scoring."""

    enabled: bool = Field(True, description="Whether diversity scoring is enabled")
    unique_leader_bonus: float = Field(1.0, description="Bonus for unique leaders")
    duplicate_leader_penalty: float = Field(
        0.5, description="Penalty for duplicate leaders"
    )
    mode: Literal["class", "unit_type", "assist_type"] = Field(
        "class", description="Diversity calculation mode"
    )


class CombatScoringConfig(BaseModel):
    """Configuration for combat scoring calculations."""

    role_weights: dict[str, float] = Field(
        default_factory=dict, description="Weights for combat roles"
    )
    capability_weights: dict[str, float] = Field(
        default_factory=dict, description="Weights for capabilities"
    )
    coverage: CoverageWeights = Field(
        default_factory=lambda: CoverageWeights(),
        description="Coverage scoring configuration",
    )
    diversity: DiversityWeights = Field(
        default_factory=lambda: DiversityWeights(),
        description="Diversity scoring configuration",
    )

    @field_validator("role_weights", mode="before")
    @classmethod
    def normalize_role_weights(cls, value: dict[str, float] | None) -> dict[str, float]:
        return _normalize_weights(value, "role_weights")

    @field_validator("capability_weights", mode="before")
    @classmethod
    def normalize_capability_weights(
        cls, value: dict[str, float] | None
    ) -> dict[str, float]:
        return _normalize_weights(value, "capability_weights")


class CombatDiagnostic(BaseModel):
    """Diagnostic emitted during combat scoring."""

    code: DiagnosticCode = Field(..., description="Diagnostic code")
    severity: DiagnosticSeverity = Field(..., description="Diagnostic severity")
    message: Annotated[str, Field(min_length=1, description="Diagnostic message")]
    subject: str | None = Field(
        None, description="Subject identifier for the diagnostic"
    )


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


class CoverageSummary(BaseModel):
    """Summary of army coverage scoring."""

    assist_type_counts: dict[str, int] = Field(
        default_factory=dict, description="Count of each assist type across army"
    )
    unit_type_counts: dict[str, int] = Field(
        default_factory=dict, description="Count of each unit type across army"
    )
    assist_type_score: float = Field(0.0, description="Score from assist type coverage")
    unit_type_score: float = Field(0.0, description="Score from unit type coverage")
    total_score: float = Field(0.0, description="Total coverage score")


class DiversitySummary(BaseModel):
    """Summary of leader diversity scoring."""

    leaders: list[str] = Field(default_factory=list, description="List of unit leaders")
    leader_classes: list[str] = Field(
        default_factory=list, description="Classes of unit leaders"
    )
    unique_count: int = Field(0, description="Number of unique leader classes")
    duplicate_count: int = Field(0, description="Number of duplicate leader classes")
    score: float = Field(0.0, description="Diversity score")


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
        default_factory=lambda: CoverageSummary(),
        description="Army coverage summary",
    )
    diversity: DiversitySummary = Field(
        default_factory=lambda: DiversitySummary(),
        description="Leader diversity summary",
    )

    @property
    def army_total_score(self) -> float:
        return self.total_score + self.coverage.total_score + self.diversity.score


class Solution(BaseModel):
    """Solution from the unit optimization solver."""

    units: list[list[str]] = Field(..., description="Character assignments per unit")
    unit_rapports: list[int] = Field(..., description="Rapport count per unit")
    total_rapports: int = Field(..., description="Total rapport pairs across all units")
    unassigned: list[str] = Field(
        ..., description="Characters not assigned to any unit"
    )
    seed: int = Field(..., description="Random seed used for this run")
    restarts: int = Field(..., description="Number of greedy restarts")
    swap_iterations: int = Field(
        ..., description="Number of swap improvement iterations"
    )
    combat: CombatSummary | None = Field(None, description="Combat scoring summary")


class UserMessage(BaseModel):
    """User-facing message produced by core workflows."""

    severity: Literal["warning", "info"] = Field(
        ..., description="Severity of the message"
    )
    message: Annotated[str, Field(min_length=1, description="Message text")]


class SolveRunResult(BaseModel):
    """Result of a solve workflow run."""

    solution: Solution = Field(..., description="Solved unit composition")
    unit_sizes: list[int] = Field(..., description="Unit sizes for this run")
    combat_scoring: CombatScoringConfig = Field(
        ..., description="Combat scoring configuration used"
    )
    warnings: list[UserMessage] = Field(
        default_factory=list, description="Warnings to surface to the user"
    )
    combat_diagnostics: list[CombatDiagnostic] = Field(
        default_factory=list, description="Combat diagnostics to surface"
    )


class BenchmarkStatsSummary(BaseModel):
    """Summary stats for benchmark outputs."""

    count: int = Field(..., description="Number of samples")
    min: float = Field(..., description="Minimum score observed")
    max: float = Field(..., description="Maximum score observed")
    mean: float = Field(..., description="Mean score across samples")
    p50: float = Field(..., description="Median score")
    p75: float = Field(..., description="75th percentile score")
    p90: float = Field(..., description="90th percentile score")
    std: float = Field(..., description="Standard deviation of scores")


class BenchmarkInputSummary(BaseModel):
    """Input configuration for benchmark runs."""

    seed: int = Field(..., description="Random seed used")
    units: list[int] = Field(..., description="Unit sizes used in the benchmark")
    trials: int = Field(..., description="Number of full assignment trials")
    unit_samples: int = Field(..., description="Samples per unit size")


class BenchmarkSampleCounts(BaseModel):
    """Sample counts for benchmark runs."""

    total_trials: int = Field(..., description="Total trials requested")
    total_successes: int = Field(..., description="Successful trials")
    total_failures: int = Field(..., description="Failed trials")


class UnitSizeReport(BaseModel):
    """Benchmark summary for a specific unit size."""

    stats: BenchmarkStatsSummary = Field(
        ..., description="Statistical summary for this unit size"
    )
    recommended_min: float = Field(
        ..., description="Recommended minimum score for this size"
    )
    recommended_strict: float = Field(
        ..., description="Recommended strict minimum score for this size"
    )
    samples: int = Field(..., description="Number of samples used")


class BenchmarkReport(BaseModel):
    """Benchmark report payload for JSON output."""

    combat_available: bool = Field(..., description="Whether combat data was available")
    inputs: BenchmarkInputSummary = Field(
        ..., description="Input configuration for the benchmark"
    )
    sample_counts: BenchmarkSampleCounts = Field(
        ..., description="Sample count summary"
    )
    total_score_stats: BenchmarkStatsSummary = Field(
        ..., description="Overall score stats"
    )
    recommended_min_total: float = Field(
        ..., description="Recommended minimum total score"
    )
    recommended_strict_total: float = Field(
        ..., description="Recommended strict minimum total score"
    )
    per_unit_size: dict[str, UnitSizeReport] = Field(
        default_factory=dict, description="Per-unit size benchmark results"
    )


class BenchmarkRunResult(BaseModel):
    """Result of a benchmark workflow run."""

    report: BenchmarkReport = Field(..., description="Benchmark report payload")
    summary_lines: list[str] = Field(
        default_factory=list, description="Summary lines for text output"
    )
    warnings: list[UserMessage] = Field(
        default_factory=list, description="Warnings to surface to the user"
    )
    combat_diagnostics: list[CombatDiagnostic] = Field(
        default_factory=list, description="Combat diagnostics to surface"
    )


class RapportSyncStats(BaseModel):
    """Statistics for rapport synchronization."""

    added_pairs: int = Field(..., description="Number of reciprocal pairs added")
    added_entries: int = Field(..., description="Number of new rapport entries added")
    duplicate_entries: int = Field(
        ..., description="Number of duplicate entries collapsed"
    )
    skipped_self: int = Field(..., description="Number of self-pairs removed")
    skipped_unknown: int = Field(
        ..., description="Number of pairs with unknown ids skipped"
    )
    unknown_entry_ids: int = Field(
        ..., description="Number of rapport entries with unknown ids"
    )


class RapportSyncResult(BaseModel):
    """Result of rapport synchronization."""

    normalized: list[RapportListEntry] = Field(
        default_factory=list, description="Normalized rapport entries"
    )
    stats: RapportSyncStats = Field(..., description="Normalization statistics")
    changed: bool = Field(
        ..., description="Whether normalization changed the rapport list"
    )
