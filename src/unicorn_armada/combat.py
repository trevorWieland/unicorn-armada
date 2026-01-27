from __future__ import annotations

from .models import (
    ClassDefinition,
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
            unknown_members.append(member)
            continue
        class_family = class_index.get(class_id)
        if class_family is None:
            unknown_members.append(member)
            continue
        for role in class_family.roles:
            roles[role] = roles.get(role, 0) + 1
        capability_set = set(class_family.capabilities)
        if class_family.assist_type != "none":
            capability_set.add("assist")
        if class_family.unit_type == "cavalry":
            capability_set.add("cavalry")
        if class_family.unit_type == "flying":
            capability_set.add("flying")
        if "archer" in class_family.class_types:
            capability_set.add("archer")
        if "caster" in class_family.class_types:
            capability_set.add("caster")

        for capability in capability_set:
            capabilities[capability] = capabilities.get(capability, 0) + 1

    return roles, capabilities, sorted(unknown_members)


def _score_unit_tags(
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


def compute_army_coverage(
    units: list[list[str]],
    character_classes: dict[str, str],
    class_index: dict[str, ClassDefinition],
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
    unknown_members = 0

    for unit in units:
        for member in unit:
            class_id = character_classes.get(member)
            if not class_id:
                unknown_members += 1
                continue
            class_family = class_index.get(class_id)
            if class_family is None:
                unknown_members += 1
                continue

            # Count assist types
            assist = class_family.assist_type
            if assist != "none":
                assist_type_counts[assist] = assist_type_counts.get(assist, 0) + 1

            # Count unit types
            unit_type = class_family.unit_type
            unit_type_counts[unit_type] = unit_type_counts.get(unit_type, 0) + 1

    # Score coverage based on unique types present
    assist_type_score = 0.0
    for type_name, weight in weights.assist_type_weights.items():
        if type_name in assist_type_counts:
            assist_type_score += weight

    unit_type_score = 0.0
    for type_name, weight in weights.unit_type_weights.items():
        if type_name in unit_type_counts:
            unit_type_score += weight

    if unknown_members > 0:
        total_members = sum(len(unit) for unit in units)
        if unknown_members / total_members > 0.5:
            # Warning but don't fail - graceful degradation
            pass  # Could log warning

    return CoverageSummary(
        assist_type_counts=dict(sorted(assist_type_counts.items())),
        unit_type_counts=dict(sorted(unit_type_counts.items())),
        assist_type_score=assist_type_score,
        unit_type_score=unit_type_score,
        total_score=assist_type_score + unit_type_score,
    )


def select_leader_for_unit(
    unit: list[str],
    character_classes: dict[str, str],
    class_index: dict[str, ClassDefinition],
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
        class_id = character_classes.get(member)
        if not class_id:
            continue
        class_family = class_index.get(class_id)
        if class_family and class_family.leader_effect:
            return member

    # Fallback: first character with valid class
    for member in unit:
        class_id = character_classes.get(member)
        if class_id and class_id in class_index:
            return member

    return unit[0]  # Last resort


def compute_leader_diversity(
    units: list[list[str]],
    character_classes: dict[str, str],
    class_index: dict[str, ClassDefinition],
    weights: DiversityWeights,
) -> DiversitySummary:
    """
    Compute diversity score based on leader uniqueness.
    Higher score = more unique leader classes across units.
    """
    leaders: list[str] = []
    leader_classes: list[str] = []

    for unit in units:
        leader = select_leader_for_unit(unit, character_classes, class_index)
        if leader:
            leaders.append(leader)

            # Determine leader identifier based on mode
            class_id = character_classes.get(leader)
            if class_id and class_id in class_index:
                class_family = class_index[class_id]
                if weights.mode == "class":
                    leader_id = class_id
                elif weights.mode == "unit_type":
                    leader_id = class_family.unit_type
                elif weights.mode == "assist_type":
                    leader_id = class_family.assist_type
                else:
                    leader_id = class_id
            else:
                leader_id = "unknown"

            leader_classes.append(leader_id)

    # Calculate diversity
    unique_classes = set(leader_classes)
    duplicate_count = len(leader_classes) - len(unique_classes)

    # Score: bonus for each unique, penalty for duplicates
    score = len(unique_classes) * weights.unique_leader_bonus
    score -= duplicate_count * weights.duplicate_leader_penalty

    return DiversitySummary(
        leaders=leaders,
        leader_classes=leader_classes,
        unique_count=len(unique_classes),
        duplicate_count=duplicate_count,
        score=max(score, 0.0),  # Floor at 0
    )


def compute_combat_summary(
    units: list[list[str]],
    character_classes: dict[str, str],
    classes: list[ClassDefinition],
    scoring: CombatScoringConfig,
) -> CombatSummary:
    class_index = build_class_index(classes)
    unit_scores: list[float] = []
    unit_breakdowns: list[CombatUnitBreakdown] = []

    for unit in units:
        roles, capabilities, unknown_members = _count_unit_tags(
            unit, character_classes, class_index
        )
        score = _score_unit_tags(roles, capabilities, scoring)
        unit_scores.append(score)
        unit_breakdowns.append(
            CombatUnitBreakdown(
                roles=dict(sorted(roles.items())),
                capabilities=dict(sorted(capabilities.items())),
                unknown_members=unknown_members,
                score=score,
            )
        )

    # Army-level coverage scoring
    coverage_summary = CoverageSummary()
    if scoring.coverage.enabled and classes and character_classes:
        coverage_summary = compute_army_coverage(
            units, character_classes, class_index, scoring.coverage
        )

    # Army-level diversity scoring
    diversity_summary = DiversitySummary()
    if scoring.diversity.enabled and classes and character_classes:
        diversity_summary = compute_leader_diversity(
            units, character_classes, class_index, scoring.diversity
        )

    return CombatSummary(
        unit_scores=unit_scores,
        unit_breakdowns=unit_breakdowns,
        total_score=sum(unit_scores),
        coverage=coverage_summary,
        diversity=diversity_summary,
    )
