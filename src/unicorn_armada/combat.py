from __future__ import annotations

from typing import Protocol

from .models import (
    ClassContext,
    ClassDefinition,
    CombatDiagnostic,
    CombatScoringConfig,
    CombatSummary,
    CombatUnitBreakdown,
    CoverageSummary,
    CoverageWeights,
    DiversitySummary,
    DiversityWeights,
)


def build_class_index(classes: list[ClassDefinition]) -> dict[str, ClassDefinition]:
    return {entry.id: entry for entry in classes}


def build_class_context(entry: ClassDefinition) -> ClassContext:
    capabilities = list(entry.capabilities)
    seen = set(capabilities)

    def _add_capability(tag: str) -> None:
        if tag in seen:
            return
        seen.add(tag)
        capabilities.append(tag)

    if entry.assist_type != "none":
        _add_capability("assist")
    if entry.unit_type == "cavalry":
        _add_capability("cavalry")
    if entry.unit_type == "flying":
        _add_capability("flying")
    if "archer" in entry.class_types:
        _add_capability("archer")
    if "caster" in entry.class_types:
        _add_capability("caster")

    return ClassContext(
        class_id=entry.id,
        roles=list(entry.roles),
        capabilities=capabilities,
        class_types=list(entry.class_types),
        unit_type=entry.unit_type,
        assist_type=entry.assist_type,
        has_leader_effect=entry.leader_effect is not None,
    )


def build_class_context_index(
    classes: list[ClassDefinition],
) -> dict[str, ClassContext]:
    return {entry.id: build_class_context(entry) for entry in classes}


def missing_class_mapping_diagnostic(member: str) -> CombatDiagnostic:
    return CombatDiagnostic(
        code="missing_class_mapping",
        severity="error",
        message=f"Character '{member}' has no class mapping",
        subject=member,
    )


def unknown_class_id_diagnostic(member: str, class_id: str) -> CombatDiagnostic:
    return CombatDiagnostic(
        code="unknown_class_id",
        severity="error",
        message=f"Character '{member}' has unknown class '{class_id}'",
        subject=member,
    )


def missing_default_classes_diagnostic(
    missing_ids: set[str],
) -> CombatDiagnostic:
    formatted = ", ".join(sorted(missing_ids))
    return CombatDiagnostic(
        code="missing_default_classes",
        severity="warning",
        message=f"missing default classes for roster characters: {formatted}",
        subject=None,
    )


def format_diagnostic(diagnostic: CombatDiagnostic) -> str:
    if diagnostic.severity == "warning":
        return f"Warning: {diagnostic.message}"
    return diagnostic.message


def _resolve_member_context(
    member: str,
    character_classes: dict[str, str],
    class_context_index: dict[str, ClassContext],
    *,
    allow_missing: bool,
) -> ClassContext | None:
    class_id = character_classes.get(member)
    if not class_id:
        if allow_missing:
            return None
        diagnostic = missing_class_mapping_diagnostic(member)
        raise ValueError(diagnostic.message)
    class_context = class_context_index.get(class_id)
    if class_context is None:
        if allow_missing:
            return None
        diagnostic = unknown_class_id_diagnostic(member, class_id)
        raise ValueError(diagnostic.message)
    return class_context


def _resolve_unit_contexts(
    unit: list[str],
    character_classes: dict[str, str],
    class_context_index: dict[str, ClassContext],
) -> list[ClassContext]:
    contexts: list[ClassContext] = []
    for member in unit:
        context = _resolve_member_context(
            member,
            character_classes,
            class_context_index,
            allow_missing=False,
        )
        if context is not None:
            contexts.append(context)
    return contexts


def count_unit_tags(
    unit_contexts: list[ClassContext],
) -> tuple[dict[str, int], dict[str, int]]:
    roles: dict[str, int] = {}
    capabilities: dict[str, int] = {}

    for context in unit_contexts:
        for role in context.roles:
            roles[role] = roles.get(role, 0) + 1
        for capability in context.capabilities:
            capabilities[capability] = capabilities.get(capability, 0) + 1

    return roles, capabilities


def score_unit_tags(
    roles: dict[str, int],
    capabilities: dict[str, int],
    scoring: CombatScoringConfig,
) -> float:
    score = 0.0
    for role, weight in scoring.role_weights.items():
        if roles.get(role, 0) > 0:
            score += weight
    for capability, weight in scoring.capability_weights.items():
        if capabilities.get(capability, 0) > 0:
            score += weight
    return score


def empty_coverage_summary() -> CoverageSummary:
    return CoverageSummary(
        assist_type_counts={},
        unit_type_counts={},
        assist_type_score=0.0,
        unit_type_score=0.0,
        total_score=0.0,
    )


def empty_diversity_summary() -> DiversitySummary:
    return DiversitySummary(
        leaders=[],
        leader_classes=[],
        unique_count=0,
        duplicate_count=0,
        score=0.0,
    )


def compute_army_coverage_from_contexts(
    units: list[list[str]],
    character_classes: dict[str, str],
    class_context_index: dict[str, ClassContext],
    weights: CoverageWeights,
) -> CoverageSummary:
    """
    Compute army-level coverage for assist types and unit types.

    Scoring: sum(unique_type_count * weight) for each type category.
    With target_multiplier=1.0 (soft), bonuses accumulate without cap.
    With target_multiplier=0.0 (hard), only up to target types count.
    """
    assist_type_counts: dict[str, int] = {}
    unit_type_counts: dict[str, int] = {}

    for unit in units:
        for member in unit:
            context = _resolve_member_context(
                member,
                character_classes,
                class_context_index,
                allow_missing=False,
            )
            if context is None:
                continue

            assist = context.assist_type
            if assist != "none":
                assist_type_counts[assist] = assist_type_counts.get(assist, 0) + 1

            unit_type = context.unit_type
            unit_type_counts[unit_type] = unit_type_counts.get(unit_type, 0) + 1

    assist_type_score = 0.0
    for type_name, weight in weights.assist_type_weights.items():
        if type_name in assist_type_counts:
            assist_type_score += weight

    unit_type_score = 0.0
    for type_name, weight in weights.unit_type_weights.items():
        if type_name in unit_type_counts:
            unit_type_score += weight

    return CoverageSummary(
        assist_type_counts=dict(sorted(assist_type_counts.items())),
        unit_type_counts=dict(sorted(unit_type_counts.items())),
        assist_type_score=assist_type_score,
        unit_type_score=unit_type_score,
        total_score=assist_type_score + unit_type_score,
    )


def select_leader_for_unit_context(
    unit: list[str],
    character_classes: dict[str, str],
    class_context_index: dict[str, ClassContext],
) -> str | None:
    """
    Select leader for a unit.
    Priority:
    1. First character with leader_effect (explicit leader)
    2. First character with valid class data
    3. First character in list
    """
    if not unit:
        return None

    for member in unit:
        context = _resolve_member_context(
            member,
            character_classes,
            class_context_index,
            allow_missing=True,
        )
        if context and context.has_leader_effect:
            return member

    for member in unit:
        context = _resolve_member_context(
            member,
            character_classes,
            class_context_index,
            allow_missing=True,
        )
        if context is not None:
            return member

    return unit[0]


def compute_leader_diversity_from_contexts(
    units: list[list[str]],
    character_classes: dict[str, str],
    class_context_index: dict[str, ClassContext],
    weights: DiversityWeights,
) -> DiversitySummary:
    """
    Compute diversity score based on leader uniqueness.
    Higher score = more unique leader classes across units.
    """
    leaders: list[str] = []
    leader_classes: list[str] = []

    for unit in units:
        leader = select_leader_for_unit_context(
            unit,
            character_classes,
            class_context_index,
        )
        if leader:
            leaders.append(leader)

            class_id = character_classes.get(leader)
            if not class_id:
                diagnostic = missing_class_mapping_diagnostic(leader)
                raise ValueError(diagnostic.message)
            context = class_context_index.get(class_id)
            if context is None:
                diagnostic = unknown_class_id_diagnostic(leader, class_id)
                raise ValueError(diagnostic.message)

            if weights.mode == "class":
                leader_id = class_id
            elif weights.mode == "unit_type":
                leader_id = context.unit_type
            elif weights.mode == "assist_type":
                leader_id = context.assist_type
            else:
                leader_id = class_id

            leader_classes.append(leader_id)

    unique_classes = set(leader_classes)
    duplicate_count = len(leader_classes) - len(unique_classes)

    score = len(unique_classes) * weights.unique_leader_bonus
    score -= duplicate_count * weights.duplicate_leader_penalty

    return DiversitySummary(
        leaders=leaders,
        leader_classes=leader_classes,
        unique_count=len(unique_classes),
        duplicate_count=duplicate_count,
        score=max(score, 0.0),
    )


class UnitScoreFeature(Protocol):
    key: str

    def is_enabled(self, scoring: CombatScoringConfig) -> bool: ...

    def compute(
        self,
        unit_contexts: list[ClassContext],
        scoring: CombatScoringConfig,
    ) -> CombatUnitBreakdown: ...


class ArmyScoreFeature(Protocol):
    key: str

    def is_enabled(self, scoring: CombatScoringConfig) -> bool: ...

    def compute(
        self,
        units: list[list[str]],
        character_classes: dict[str, str],
        class_context_index: dict[str, ClassContext],
        scoring: CombatScoringConfig,
    ) -> CoverageSummary | DiversitySummary: ...


class FeatureRegistry:
    def __init__(self) -> None:
        self._unit_features: list[UnitScoreFeature] = []
        self._army_features: list[ArmyScoreFeature] = []

    def register_unit(self, feature: UnitScoreFeature) -> None:
        self._unit_features.append(feature)

    def register_army(self, feature: ArmyScoreFeature) -> None:
        self._army_features.append(feature)

    def compute_unit_breakdown(
        self,
        unit_contexts: list[ClassContext],
        scoring: CombatScoringConfig,
    ) -> CombatUnitBreakdown:
        roles: dict[str, int] = {}
        capabilities: dict[str, int] = {}
        unknown_members: set[str] = set()
        total_score = 0.0

        for feature in self._unit_features:
            if not feature.is_enabled(scoring):
                continue
            breakdown = feature.compute(unit_contexts, scoring)
            total_score += breakdown.score
            for role, count in breakdown.roles.items():
                roles[role] = roles.get(role, 0) + count
            for capability, count in breakdown.capabilities.items():
                capabilities[capability] = capabilities.get(capability, 0) + count
            unknown_members.update(breakdown.unknown_members)

        return CombatUnitBreakdown(
            roles=dict(sorted(roles.items())),
            capabilities=dict(sorted(capabilities.items())),
            unknown_members=sorted(unknown_members),
            score=total_score,
        )

    def compute_army_summaries(
        self,
        units: list[list[str]],
        character_classes: dict[str, str],
        class_context_index: dict[str, ClassContext],
        scoring: CombatScoringConfig,
    ) -> tuple[CoverageSummary, DiversitySummary]:
        coverage = empty_coverage_summary()
        diversity = empty_diversity_summary()

        for feature in self._army_features:
            if not feature.is_enabled(scoring):
                continue
            result = feature.compute(
                units,
                character_classes,
                class_context_index,
                scoring,
            )
            if isinstance(result, CoverageSummary):
                coverage = result
            elif isinstance(result, DiversitySummary):
                diversity = result

        return coverage, diversity


class UnitTagFeature:
    key = "unit_tags"

    def is_enabled(self, scoring: CombatScoringConfig) -> bool:
        return True

    def compute(
        self,
        unit_contexts: list[ClassContext],
        scoring: CombatScoringConfig,
    ) -> CombatUnitBreakdown:
        roles, capabilities = count_unit_tags(unit_contexts)
        score = score_unit_tags(roles, capabilities, scoring)
        return CombatUnitBreakdown(
            roles=roles,
            capabilities=capabilities,
            unknown_members=[],
            score=score,
        )


class CoverageFeature:
    key = "coverage"

    def is_enabled(self, scoring: CombatScoringConfig) -> bool:
        return scoring.coverage.enabled

    def compute(
        self,
        units: list[list[str]],
        character_classes: dict[str, str],
        class_context_index: dict[str, ClassContext],
        scoring: CombatScoringConfig,
    ) -> CoverageSummary:
        return compute_army_coverage_from_contexts(
            units,
            character_classes,
            class_context_index,
            scoring.coverage,
        )


class DiversityFeature:
    key = "diversity"

    def is_enabled(self, scoring: CombatScoringConfig) -> bool:
        return scoring.diversity.enabled

    def compute(
        self,
        units: list[list[str]],
        character_classes: dict[str, str],
        class_context_index: dict[str, ClassContext],
        scoring: CombatScoringConfig,
    ) -> DiversitySummary:
        return compute_leader_diversity_from_contexts(
            units,
            character_classes,
            class_context_index,
            scoring.diversity,
        )


def build_scoring_registry() -> FeatureRegistry:
    registry = FeatureRegistry()
    registry.register_unit(UnitTagFeature())
    registry.register_army(CoverageFeature())
    registry.register_army(DiversityFeature())
    return registry


def _count_unit_tags(
    unit: list[str],
    character_classes: dict[str, str],
    class_index: dict[str, ClassDefinition],
) -> tuple[dict[str, int], dict[str, int], list[str]]:
    class_context_index = build_class_context_index(list(class_index.values()))
    unit_contexts = _resolve_unit_contexts(
        unit,
        character_classes,
        class_context_index,
    )
    roles, capabilities = count_unit_tags(unit_contexts)
    return roles, capabilities, []


def _score_unit_tags(
    roles: dict[str, int],
    capabilities: dict[str, int],
    scoring: CombatScoringConfig,
) -> float:
    return score_unit_tags(roles, capabilities, scoring)


def compute_army_coverage(
    units: list[list[str]],
    character_classes: dict[str, str],
    class_index: dict[str, ClassDefinition],
    weights: CoverageWeights,
) -> CoverageSummary:
    class_context_index = build_class_context_index(list(class_index.values()))
    return compute_army_coverage_from_contexts(
        units,
        character_classes,
        class_context_index,
        weights,
    )


def select_leader_for_unit(
    unit: list[str],
    character_classes: dict[str, str],
    class_index: dict[str, ClassDefinition],
) -> str | None:
    class_context_index = build_class_context_index(list(class_index.values()))
    return select_leader_for_unit_context(
        unit,
        character_classes,
        class_context_index,
    )


def compute_leader_diversity(
    units: list[list[str]],
    character_classes: dict[str, str],
    class_index: dict[str, ClassDefinition],
    weights: DiversityWeights,
) -> DiversitySummary:
    class_context_index = build_class_context_index(list(class_index.values()))
    return compute_leader_diversity_from_contexts(
        units,
        character_classes,
        class_context_index,
        weights,
    )


def compute_combat_summary(
    units: list[list[str]],
    character_classes: dict[str, str],
    classes: list[ClassDefinition],
    scoring: CombatScoringConfig,
) -> CombatSummary:
    class_context_index = build_class_context_index(classes)
    registry = build_scoring_registry()
    unit_scores: list[float] = []
    unit_breakdowns: list[CombatUnitBreakdown] = []

    for unit in units:
        unit_contexts = _resolve_unit_contexts(
            unit,
            character_classes,
            class_context_index,
        )
        breakdown = registry.compute_unit_breakdown(unit_contexts, scoring)
        unit_scores.append(breakdown.score)
        unit_breakdowns.append(breakdown)

    coverage_summary = empty_coverage_summary()
    diversity_summary = empty_diversity_summary()
    if classes and character_classes:
        coverage_summary, diversity_summary = registry.compute_army_summaries(
            units,
            character_classes,
            class_context_index,
            scoring,
        )

    return CombatSummary(
        unit_scores=unit_scores,
        unit_breakdowns=unit_breakdowns,
        total_score=sum(unit_scores),
        coverage=coverage_summary,
        diversity=diversity_summary,
    )
