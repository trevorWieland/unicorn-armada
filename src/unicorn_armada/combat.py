from __future__ import annotations

from .models import (
    ClassDefinition,
    CombatScoringConfig,
    CombatSummary,
    CombatUnitBreakdown,
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

    return CombatSummary(
        unit_scores=unit_scores,
        unit_breakdowns=unit_breakdowns,
        total_score=sum(unit_scores),
    )
