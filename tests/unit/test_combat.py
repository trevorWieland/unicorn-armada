"""Unit tests for combat module."""

from __future__ import annotations

import pytest

from unicorn_armada.combat import (
    _count_unit_tags,
    _score_unit_tags,
    build_class_index,
    compute_army_coverage,
    compute_combat_summary,
    compute_leader_diversity,
    select_leader_for_unit,
)
from unicorn_armada.models import (
    ClassDefinition,
    CombatScoringConfig,
    CoverageWeights,
    DiversityWeights,
    LeaderEffect,
)

# --- Fixtures ---


@pytest.fixture
def sample_classes() -> list[ClassDefinition]:
    """Sample class definitions for testing."""
    return [
        ClassDefinition(
            id="knight",
            roles=["frontline", "tank"],
            capabilities=["guard"],
            unit_type="infantry",
            assist_type="none",
            class_types=["melee"],
            leader_effect=LeaderEffect(name="Rally", description="Boosts morale"),
            stamina=100,
            mobility=3,
        ),
        ClassDefinition(
            id="archer",
            roles=["backline", "dps"],
            capabilities=["ranged"],
            unit_type="infantry",
            assist_type="ranged",
            class_types=["archer"],
            leader_effect=None,
            stamina=80,
            mobility=4,
        ),
        ClassDefinition(
            id="mage",
            roles=["backline", "support"],
            capabilities=["aoe"],
            unit_type="infantry",
            assist_type="magick",
            class_types=["caster"],
            leader_effect=None,
            stamina=60,
            mobility=3,
        ),
        ClassDefinition(
            id="cavalry",
            roles=["frontline", "dps"],
            capabilities=["charge"],
            unit_type="cavalry",
            assist_type="none",
            class_types=["melee"],
            leader_effect=None,
            stamina=90,
            mobility=6,
        ),
        ClassDefinition(
            id="pegasus",
            roles=["backline", "support"],
            capabilities=["heal"],
            unit_type="flying",
            assist_type="healing",
            class_types=["healer"],
            leader_effect=LeaderEffect(name="Grace", description="Healing aura"),
            stamina=70,
            mobility=5,
        ),
    ]


@pytest.fixture
def sample_class_index(
    sample_classes: list[ClassDefinition],
) -> dict[str, ClassDefinition]:
    """Class index from sample classes."""
    return build_class_index(sample_classes)


@pytest.fixture
def sample_character_classes() -> dict[str, str]:
    """Character to class mapping."""
    return {
        "alice": "knight",
        "bob": "archer",
        "charlie": "mage",
        "dave": "cavalry",
        "eve": "pegasus",
    }


@pytest.fixture
def default_scoring() -> CombatScoringConfig:
    """Default scoring config."""
    return CombatScoringConfig()


# --- Tests for build_class_index ---


class TestBuildClassIndex:
    """Tests for build_class_index function."""

    def test_empty_list(self) -> None:
        """Empty class list should return empty index."""
        index = build_class_index([])
        assert index == {}

    def test_single_class(self) -> None:
        """Single class should be indexed by id."""
        classes = [
            ClassDefinition(
                id="knight",
                roles=["frontline"],
                class_types=["melee"],
                unit_type="infantry",
                assist_type="none",
                stamina=100,
                mobility=3,
            )
        ]
        index = build_class_index(classes)
        assert "knight" in index
        assert index["knight"].id == "knight"

    def test_multiple_classes(self, sample_classes: list[ClassDefinition]) -> None:
        """Multiple classes should all be indexed."""
        index = build_class_index(sample_classes)
        assert len(index) == 5
        assert "knight" in index
        assert "archer" in index
        assert "mage" in index

    def test_duplicate_ids_last_wins(self) -> None:
        """Duplicate ids should use last definition."""
        classes = [
            ClassDefinition(
                id="knight",
                roles=["first"],
                class_types=["melee"],
                unit_type="infantry",
                assist_type="none",
                stamina=100,
                mobility=3,
            ),
            ClassDefinition(
                id="knight",
                roles=["second"],
                class_types=["melee"],
                unit_type="infantry",
                assist_type="none",
                stamina=100,
                mobility=3,
            ),
        ]
        index = build_class_index(classes)
        assert index["knight"].roles == ["second"]


# --- Tests for _count_unit_tags ---


class TestCountUnitTags:
    """Tests for _count_unit_tags function."""

    def test_empty_unit(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Empty unit should return empty counts."""
        roles, capabilities, unknown = _count_unit_tags(
            [], sample_character_classes, sample_class_index
        )
        assert roles == {}
        assert capabilities == {}
        assert unknown == []

    def test_single_known_member(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Single known member should have their roles and capabilities counted."""
        roles, capabilities, unknown = _count_unit_tags(
            ["alice"], sample_character_classes, sample_class_index
        )
        assert roles == {"frontline": 1, "tank": 1}
        assert "guard" in capabilities
        assert unknown == []

    def test_unknown_character(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Unknown character should be in unknown list."""
        roles, capabilities, unknown = _count_unit_tags(
            ["unknown_char"], sample_character_classes, sample_class_index
        )
        assert roles == {}
        assert capabilities == {}
        assert unknown == ["unknown_char"]

    def test_missing_class_definition(
        self,
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Character with class not in index should be unknown."""
        char_classes = {"alice": "nonexistent_class"}
        roles, capabilities, unknown = _count_unit_tags(
            ["alice"], char_classes, sample_class_index
        )
        assert unknown == ["alice"]
        del roles, capabilities  # Silence unused variable warnings

    def test_assist_type_adds_assist_capability(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Characters with assist_type != 'none' should get assist capability."""
        roles, capabilities, unknown = _count_unit_tags(
            ["bob"],
            sample_character_classes,
            sample_class_index,  # archer has ranged assist
        )
        assert "assist" in capabilities
        del roles, unknown  # Silence unused variable warnings

    def test_cavalry_adds_cavalry_capability(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Cavalry unit type should add cavalry capability."""
        roles, capabilities, unknown = _count_unit_tags(
            ["dave"], sample_character_classes, sample_class_index
        )
        assert "cavalry" in capabilities
        del roles, unknown  # Silence unused variable warnings

    def test_flying_adds_flying_capability(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Flying unit type should add flying capability."""
        roles, capabilities, unknown = _count_unit_tags(
            ["eve"], sample_character_classes, sample_class_index
        )
        assert "flying" in capabilities
        del roles, unknown  # Silence unused variable warnings

    def test_archer_class_type_adds_capability(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Archer class type should add archer capability."""
        roles, capabilities, unknown = _count_unit_tags(
            ["bob"], sample_character_classes, sample_class_index
        )
        assert "archer" in capabilities
        del roles, unknown  # Silence unused variable warnings

    def test_caster_class_type_adds_capability(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Caster class type should add caster capability."""
        roles, capabilities, unknown = _count_unit_tags(
            ["charlie"], sample_character_classes, sample_class_index
        )
        assert "caster" in capabilities
        del roles, unknown  # Silence unused variable warnings

    def test_multiple_members_aggregate_counts(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Multiple members should aggregate role counts."""
        roles, capabilities, unknown = _count_unit_tags(
            ["alice", "dave"],  # both have frontline role
            sample_character_classes,
            sample_class_index,
        )
        assert roles["frontline"] == 2
        assert unknown == []
        del capabilities  # Silence unused variable warning

    def test_unknown_members_sorted(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Unknown members should be sorted alphabetically."""
        roles, capabilities, unknown = _count_unit_tags(
            ["zack", "alice", "unknown"],
            sample_character_classes,
            sample_class_index,
        )
        assert unknown == ["unknown", "zack"]
        del roles, capabilities  # Silence unused variable warnings


# --- Tests for _score_unit_tags ---


class TestScoreUnitTags:
    """Tests for _score_unit_tags function."""

    def test_empty_counts_zero_score(
        self, default_scoring: CombatScoringConfig
    ) -> None:
        """Empty role and capability counts should return 0."""
        score = _score_unit_tags({}, {}, default_scoring)
        assert score == 0.0

    def test_role_weights_applied(self) -> None:
        """Roles with weight should contribute to score."""
        scoring = CombatScoringConfig(role_weights={"frontline": 10.0, "backline": 5.0})
        score = _score_unit_tags({"frontline": 1}, {}, scoring)
        assert score == 10.0

    def test_capability_weights_applied(self) -> None:
        """Capabilities with weight should contribute to score."""
        scoring = CombatScoringConfig(capability_weights={"guard": 8.0})
        score = _score_unit_tags({}, {"guard": 1}, scoring)
        assert score == 8.0

    def test_combined_role_and_capability(self) -> None:
        """Both roles and capabilities should contribute."""
        scoring = CombatScoringConfig(
            role_weights={"frontline": 10.0},
            capability_weights={"guard": 5.0},
        )
        score = _score_unit_tags({"frontline": 2}, {"guard": 1}, scoring)
        assert score == 15.0

    def test_missing_role_not_counted(self) -> None:
        """Roles not present should not contribute."""
        scoring = CombatScoringConfig(role_weights={"frontline": 10.0, "backline": 5.0})
        score = _score_unit_tags({"backline": 1}, {}, scoring)
        assert score == 5.0

    def test_count_ignored_only_presence_matters(self) -> None:
        """Only presence matters, not count (weight applied once per role)."""
        scoring = CombatScoringConfig(role_weights={"frontline": 10.0})
        score = _score_unit_tags({"frontline": 5}, {}, scoring)
        assert score == 10.0  # Not 50.0


# --- Tests for compute_army_coverage ---


class TestComputeArmyCoverage:
    """Tests for compute_army_coverage function."""

    def test_empty_units(self, sample_class_index: dict[str, ClassDefinition]) -> None:
        """Empty units should return zero coverage."""
        coverage = compute_army_coverage([], {}, sample_class_index, CoverageWeights())
        assert coverage.assist_type_counts == {}
        assert coverage.unit_type_counts == {}
        assert coverage.total_score == 0.0

    def test_single_unit_coverage(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Single unit should contribute to coverage counts."""
        weights = CoverageWeights(
            assist_type_weights={"ranged": 5.0},
            unit_type_weights={"infantry": 3.0},
        )
        coverage = compute_army_coverage(
            [["bob"]],  # archer - ranged assist, infantry
            sample_character_classes,
            sample_class_index,
            weights,
        )
        assert coverage.assist_type_counts == {"ranged": 1}
        assert coverage.unit_type_counts == {"infantry": 1}
        assert coverage.assist_type_score == 5.0
        assert coverage.unit_type_score == 3.0

    def test_multiple_units_aggregate_counts(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Multiple units should aggregate type counts."""
        weights = CoverageWeights()
        coverage = compute_army_coverage(
            [["alice"], ["bob"]],  # knight (infantry, none), archer (infantry, ranged)
            sample_character_classes,
            sample_class_index,
            weights,
        )
        assert coverage.unit_type_counts["infantry"] == 2
        assert coverage.assist_type_counts == {"ranged": 1}

    def test_none_assist_type_not_counted(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """assist_type='none' should not be counted."""
        weights = CoverageWeights()
        coverage = compute_army_coverage(
            [["alice"]],  # knight has assist_type='none'
            sample_character_classes,
            sample_class_index,
            weights,
        )
        assert "none" not in coverage.assist_type_counts

    def test_unknown_members_tracked(
        self,
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Unknown members should be tracked but not crash."""
        weights = CoverageWeights()
        coverage = compute_army_coverage(
            [["unknown_char"]],
            {},
            sample_class_index,
            weights,
        )
        assert coverage.assist_type_counts == {}
        assert coverage.unit_type_counts == {}

    def test_coverage_scores_sorted(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Coverage counts should be sorted alphabetically."""
        weights = CoverageWeights()
        coverage = compute_army_coverage(
            [["bob", "charlie", "eve"]],  # ranged, magick, healing
            sample_character_classes,
            sample_class_index,
            weights,
        )
        assert list(coverage.assist_type_counts.keys()) == sorted(
            coverage.assist_type_counts.keys()
        )


# --- Tests for select_leader_for_unit ---


class TestSelectLeaderForUnit:
    """Tests for select_leader_for_unit function."""

    def test_empty_unit(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Empty unit should return None."""
        leader = select_leader_for_unit(
            [], sample_character_classes, sample_class_index
        )
        assert leader is None

    def test_leader_effect_prioritized(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Character with leader_effect should be selected first."""
        # alice (knight) has leader_effect=True
        leader = select_leader_for_unit(
            ["bob", "alice", "charlie"],
            sample_character_classes,
            sample_class_index,
        )
        assert leader == "alice"

    def test_first_with_class_data_fallback(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Without leader_effect, first with valid class is selected."""
        leader = select_leader_for_unit(
            ["bob", "charlie"],  # neither has leader_effect
            sample_character_classes,
            sample_class_index,
        )
        assert leader == "bob"

    def test_first_member_last_resort(
        self,
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Without any class data, first member is selected."""
        leader = select_leader_for_unit(
            ["unknown1", "unknown2"],
            {},
            sample_class_index,
        )
        assert leader == "unknown1"

    def test_multiple_leader_effects_first_wins(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """First character with leader_effect wins."""
        # alice (knight) and eve (pegasus) both have leader_effect
        leader = select_leader_for_unit(
            ["eve", "alice"],
            sample_character_classes,
            sample_class_index,
        )
        assert leader == "eve"


# --- Tests for compute_leader_diversity ---


class TestComputeLeaderDiversity:
    """Tests for compute_leader_diversity function."""

    def test_empty_units(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Empty units should return zero diversity."""
        diversity = compute_leader_diversity(
            [],
            sample_character_classes,
            sample_class_index,
            DiversityWeights(),
        )
        assert diversity.leaders == []
        assert diversity.unique_count == 0
        assert diversity.score == 0.0

    def test_single_unit_diversity(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Single unit should have one unique leader."""
        diversity = compute_leader_diversity(
            [["alice"]],
            sample_character_classes,
            sample_class_index,
            DiversityWeights(unique_leader_bonus=10.0),
        )
        assert diversity.leaders == ["alice"]
        assert diversity.unique_count == 1
        assert diversity.score == 10.0

    def test_multiple_unique_leaders(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Multiple unique leader classes should accumulate bonus."""
        diversity = compute_leader_diversity(
            [["alice"], ["bob"], ["charlie"]],
            sample_character_classes,
            sample_class_index,
            DiversityWeights(unique_leader_bonus=5.0),
        )
        assert diversity.unique_count == 3
        assert diversity.score == 15.0

    def test_duplicate_leaders_penalized(
        self,
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Duplicate leader classes should incur penalty."""
        char_classes = {"a": "knight", "b": "knight", "c": "knight"}
        diversity = compute_leader_diversity(
            [["a"], ["b"], ["c"]],
            char_classes,
            sample_class_index,
            DiversityWeights(unique_leader_bonus=10.0, duplicate_leader_penalty=3.0),
        )
        assert diversity.unique_count == 1
        assert diversity.duplicate_count == 2
        # Score: 1 * 10 - 2 * 3 = 4
        assert diversity.score == 4.0

    def test_score_floors_at_zero(
        self,
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Score should not go negative."""
        char_classes = {"a": "knight", "b": "knight", "c": "knight", "d": "knight"}
        diversity = compute_leader_diversity(
            [["a"], ["b"], ["c"], ["d"]],
            char_classes,
            sample_class_index,
            DiversityWeights(unique_leader_bonus=1.0, duplicate_leader_penalty=10.0),
        )
        # Score: 1 * 1 - 3 * 10 = -29, floored to 0
        assert diversity.score == 0.0

    def test_mode_class(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Mode 'class' should use class_id for diversity."""
        diversity = compute_leader_diversity(
            [["alice"], ["bob"]],
            sample_character_classes,
            sample_class_index,
            DiversityWeights(mode="class"),
        )
        assert diversity.leader_classes == ["knight", "archer"]

    def test_mode_unit_type(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Mode 'unit_type' should use unit_type for diversity."""
        diversity = compute_leader_diversity(
            [["alice"], ["dave"]],  # knight=infantry, cavalry=cavalry
            sample_character_classes,
            sample_class_index,
            DiversityWeights(mode="unit_type"),
        )
        assert set(diversity.leader_classes) == {"infantry", "cavalry"}
        assert diversity.unique_count == 2

    def test_mode_assist_type(
        self,
        sample_character_classes: dict[str, str],
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Mode 'assist_type' should use assist_type for diversity."""
        diversity = compute_leader_diversity(
            [["bob"], ["charlie"]],  # archer=ranged, mage=magick
            sample_character_classes,
            sample_class_index,
            DiversityWeights(mode="assist_type"),
        )
        assert set(diversity.leader_classes) == {"ranged", "magick"}

    def test_unknown_leader_class(
        self,
        sample_class_index: dict[str, ClassDefinition],
    ) -> None:
        """Unknown leader class should be labeled 'unknown'."""
        diversity = compute_leader_diversity(
            [["unknown_char"]],
            {},
            sample_class_index,
            DiversityWeights(),
        )
        assert diversity.leader_classes == ["unknown"]


# --- Tests for compute_combat_summary ---


class TestComputeCombatSummary:
    """Tests for compute_combat_summary function."""

    def test_empty_units(self, sample_classes: list[ClassDefinition]) -> None:
        """Empty units should return empty summary."""
        summary = compute_combat_summary([], {}, sample_classes, CombatScoringConfig())
        assert summary.unit_scores == []
        assert summary.unit_breakdowns == []
        assert summary.total_score == 0.0

    def test_single_unit_score(
        self,
        sample_classes: list[ClassDefinition],
        sample_character_classes: dict[str, str],
    ) -> None:
        """Single unit should have computed score."""
        scoring = CombatScoringConfig(role_weights={"frontline": 10.0})
        summary = compute_combat_summary(
            [["alice"]],  # knight has frontline role
            sample_character_classes,
            sample_classes,
            scoring,
        )
        assert len(summary.unit_scores) == 1
        assert summary.unit_scores[0] == 10.0
        assert summary.total_score == 10.0

    def test_multiple_units_total_score(
        self,
        sample_classes: list[ClassDefinition],
        sample_character_classes: dict[str, str],
    ) -> None:
        """Multiple units should have summed total score."""
        scoring = CombatScoringConfig(role_weights={"frontline": 10.0, "backline": 5.0})
        summary = compute_combat_summary(
            [["alice"], ["bob"]],  # knight=frontline, archer=backline
            sample_character_classes,
            sample_classes,
            scoring,
        )
        assert summary.unit_scores == [10.0, 5.0]
        assert summary.total_score == 15.0

    def test_unit_breakdown_populated(
        self,
        sample_classes: list[ClassDefinition],
        sample_character_classes: dict[str, str],
    ) -> None:
        """Unit breakdowns should have roles and capabilities."""
        summary = compute_combat_summary(
            [["alice"]],
            sample_character_classes,
            sample_classes,
            CombatScoringConfig(),
        )
        assert len(summary.unit_breakdowns) == 1
        breakdown = summary.unit_breakdowns[0]
        assert "frontline" in breakdown.roles
        assert "guard" in breakdown.capabilities

    def test_coverage_enabled_by_default(
        self,
        sample_classes: list[ClassDefinition],
        sample_character_classes: dict[str, str],
    ) -> None:
        """Coverage should be enabled by default."""
        scoring = CombatScoringConfig()
        assert scoring.coverage.enabled is True
        summary = compute_combat_summary(
            [["alice"]],
            sample_character_classes,
            sample_classes,
            scoring,
        )
        # Coverage should be computed since it's enabled
        assert summary.coverage.unit_type_counts != {}

    def test_coverage_enabled(
        self,
        sample_classes: list[ClassDefinition],
        sample_character_classes: dict[str, str],
    ) -> None:
        """Coverage should be computed when enabled."""
        scoring = CombatScoringConfig(
            coverage=CoverageWeights(enabled=True, unit_type_weights={"infantry": 5.0})
        )
        summary = compute_combat_summary(
            [["alice"]],  # knight is infantry
            sample_character_classes,
            sample_classes,
            scoring,
        )
        assert summary.coverage.unit_type_counts == {"infantry": 1}
        assert summary.coverage.unit_type_score == 5.0

    def test_diversity_enabled_by_default(
        self,
        sample_classes: list[ClassDefinition],
        sample_character_classes: dict[str, str],
    ) -> None:
        """Diversity should be enabled by default."""
        scoring = CombatScoringConfig()
        assert scoring.diversity.enabled is True
        summary = compute_combat_summary(
            [["alice"]],
            sample_character_classes,
            sample_classes,
            scoring,
        )
        # Diversity should be computed since it's enabled
        assert summary.diversity.leaders != []

    def test_diversity_enabled(
        self,
        sample_classes: list[ClassDefinition],
        sample_character_classes: dict[str, str],
    ) -> None:
        """Diversity should be computed when enabled."""
        scoring = CombatScoringConfig(
            diversity=DiversityWeights(enabled=True, unique_leader_bonus=10.0)
        )
        summary = compute_combat_summary(
            [["alice"], ["bob"]],
            sample_character_classes,
            sample_classes,
            scoring,
        )
        assert summary.diversity.unique_count == 2
        assert summary.diversity.score == 20.0

    def test_no_classes_graceful(self) -> None:
        """No class data should not crash, just return zero scores."""
        summary = compute_combat_summary(
            [["alice", "bob"]],
            {},
            [],
            CombatScoringConfig(),
        )
        assert summary.total_score == 0.0
        assert summary.unit_breakdowns[0].unknown_members == ["alice", "bob"]

    def test_coverage_disabled_explicitly(
        self,
        sample_classes: list[ClassDefinition],
        sample_character_classes: dict[str, str],
    ) -> None:
        """Coverage should not be computed when explicitly disabled."""
        scoring = CombatScoringConfig(
            coverage=CoverageWeights(enabled=False, unit_type_weights={"infantry": 5.0})
        )
        summary = compute_combat_summary(
            [["alice"]],
            sample_character_classes,
            sample_classes,
            scoring,
        )
        # Coverage should be empty since it's disabled
        assert summary.coverage.unit_type_counts == {}
        assert summary.coverage.total_score == 0.0

    def test_diversity_disabled_explicitly(
        self,
        sample_classes: list[ClassDefinition],
        sample_character_classes: dict[str, str],
    ) -> None:
        """Diversity should not be computed when explicitly disabled."""
        scoring = CombatScoringConfig(
            diversity=DiversityWeights(enabled=False, unique_leader_bonus=10.0)
        )
        summary = compute_combat_summary(
            [["alice"]],
            sample_character_classes,
            sample_classes,
            scoring,
        )
        # Diversity should be empty since it's disabled
        assert summary.diversity.leaders == []
        assert summary.diversity.score == 0.0
