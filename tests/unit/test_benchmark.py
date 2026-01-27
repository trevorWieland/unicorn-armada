"""Unit tests for benchmark module."""

from __future__ import annotations

import random

import pytest

from unicorn_armada.benchmark import (
    BenchmarkStats,
    _assign_clusters_randomly,
    compute_stats,
    generate_random_assignment,
    percentile,
    sample_unit_scores,
)
from unicorn_armada.models import (
    ClassDefinition,
    CombatScoringConfig,
    LeaderEffect,
)
from unicorn_armada.solver import Cluster, SolveError


# Helper to create a pair (frozenset of 2 strings)
def make_pair(a: str, b: str) -> frozenset[str]:
    """Create a Pair (frozenset of two strings)."""
    return frozenset({a, b})


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
    ]


@pytest.fixture
def sample_character_classes() -> dict[str, str]:
    """Character to class mapping."""
    return {
        "alice": "knight",
        "bob": "archer",
        "charlie": "knight",
        "dave": "archer",
        "eve": "knight",
        "frank": "archer",
    }


@pytest.fixture
def simple_roster() -> list[str]:
    """Simple roster for testing."""
    return ["alice", "bob", "charlie", "dave", "eve", "frank"]


@pytest.fixture
def seeded_rng() -> random.Random:
    """Seeded random number generator for reproducible tests."""
    return random.Random(42)


# --- Tests for percentile ---


class TestPercentile:
    """Tests for percentile function."""

    def test_empty_list(self) -> None:
        """Empty list should return 0.0."""
        assert percentile([], 0.5) == 0.0

    def test_single_value(self) -> None:
        """Single value should be returned for any percentile."""
        assert percentile([5.0], 0.0) == 5.0
        assert percentile([5.0], 0.5) == 5.0
        assert percentile([5.0], 1.0) == 5.0

    def test_percent_zero(self) -> None:
        """Percent 0 should return first value."""
        assert percentile([1.0, 2.0, 3.0], 0.0) == 1.0

    def test_percent_one(self) -> None:
        """Percent 1 should return last value."""
        assert percentile([1.0, 2.0, 3.0], 1.0) == 3.0

    def test_percent_negative(self) -> None:
        """Negative percent should return first value."""
        assert percentile([1.0, 2.0, 3.0], -0.5) == 1.0

    def test_percent_over_one(self) -> None:
        """Percent over 1 should return last value."""
        assert percentile([1.0, 2.0, 3.0], 1.5) == 3.0

    def test_median_odd_count(self) -> None:
        """Median of odd-length list should be middle value."""
        assert percentile([1.0, 2.0, 3.0], 0.5) == 2.0

    def test_median_even_count(self) -> None:
        """Median of even-length list should be interpolated."""
        result = percentile([1.0, 2.0, 3.0, 4.0], 0.5)
        assert result == 2.5

    def test_p75(self) -> None:
        """75th percentile should be correctly calculated."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = percentile(values, 0.75)
        assert result == 4.0

    def test_interpolation(self) -> None:
        """Percentile should interpolate between values."""
        values = [0.0, 10.0]
        assert percentile(values, 0.5) == 5.0
        assert percentile(values, 0.25) == 2.5
        assert percentile(values, 0.75) == 7.5


# --- Tests for compute_stats ---


class TestComputeStats:
    """Tests for compute_stats function."""

    def test_empty_list(self) -> None:
        """Empty list should return zero stats."""
        stats = compute_stats([])
        assert stats.count == 0
        assert stats.minimum == 0.0
        assert stats.maximum == 0.0
        assert stats.mean == 0.0
        assert stats.median == 0.0
        assert stats.std == 0.0

    def test_single_value(self) -> None:
        """Single value should have zero std."""
        stats = compute_stats([5.0])
        assert stats.count == 1
        assert stats.minimum == 5.0
        assert stats.maximum == 5.0
        assert stats.mean == 5.0
        assert stats.median == 5.0
        assert stats.std == 0.0

    def test_multiple_values(self) -> None:
        """Multiple values should calculate correct stats."""
        stats = compute_stats([1.0, 2.0, 3.0, 4.0, 5.0])
        assert stats.count == 5
        assert stats.minimum == 1.0
        assert stats.maximum == 5.0
        assert stats.mean == 3.0
        assert stats.median == 3.0

    def test_unsorted_input(self) -> None:
        """Input does not need to be sorted."""
        stats = compute_stats([5.0, 1.0, 3.0, 2.0, 4.0])
        assert stats.minimum == 1.0
        assert stats.maximum == 5.0
        assert stats.median == 3.0

    def test_std_calculation(self) -> None:
        """Standard deviation should be correctly calculated."""
        # Values: 2, 4, 4, 4, 5, 5, 7, 9 - mean=5, var=4, std=2
        stats = compute_stats([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        assert stats.mean == 5.0
        assert stats.std == 2.0

    def test_percentiles(self) -> None:
        """P75 and P90 should be correctly calculated."""
        values = list(range(1, 101))  # 1 to 100
        float_values = [float(v) for v in values]
        stats = compute_stats(float_values)
        assert stats.p75 == 75.25  # Interpolated
        assert abs(stats.p90 - 90.1) < 0.0001  # Interpolated (float comparison)


# --- Tests for BenchmarkStats ---


class TestBenchmarkStats:
    """Tests for BenchmarkStats model."""

    def test_valid_stats(self) -> None:
        """Valid stats should be created."""
        stats = BenchmarkStats(
            count=10,
            minimum=1.0,
            maximum=10.0,
            mean=5.5,
            median=5.0,
            p75=7.5,
            p90=9.0,
            std=2.5,
        )
        assert stats.count == 10
        assert stats.mean == 5.5


# --- Tests for sample_unit_scores ---


class TestSampleUnitScores:
    """Tests for sample_unit_scores function."""

    def test_empty_roster(
        self, seeded_rng: random.Random, sample_classes: list[ClassDefinition]
    ) -> None:
        """Empty roster should return empty list."""
        scores = sample_unit_scores(
            roster=[],
            unit_size=3,
            samples=10,
            rng=seeded_rng,
            character_classes={},
            classes=sample_classes,
            scoring=CombatScoringConfig(),
        )
        assert scores == []

    def test_zero_unit_size(
        self,
        simple_roster: list[str],
        seeded_rng: random.Random,
        sample_classes: list[ClassDefinition],
    ) -> None:
        """Zero unit size should return empty list."""
        scores = sample_unit_scores(
            roster=simple_roster,
            unit_size=0,
            samples=10,
            rng=seeded_rng,
            character_classes={},
            classes=sample_classes,
            scoring=CombatScoringConfig(),
        )
        assert scores == []

    def test_negative_unit_size(
        self,
        simple_roster: list[str],
        seeded_rng: random.Random,
        sample_classes: list[ClassDefinition],
    ) -> None:
        """Negative unit size should return empty list."""
        scores = sample_unit_scores(
            roster=simple_roster,
            unit_size=-1,
            samples=10,
            rng=seeded_rng,
            character_classes={},
            classes=sample_classes,
            scoring=CombatScoringConfig(),
        )
        assert scores == []

    def test_unit_size_larger_than_roster(
        self,
        simple_roster: list[str],
        seeded_rng: random.Random,
        sample_classes: list[ClassDefinition],
    ) -> None:
        """Unit size larger than roster should return empty list."""
        scores = sample_unit_scores(
            roster=simple_roster,
            unit_size=100,
            samples=10,
            rng=seeded_rng,
            character_classes={},
            classes=sample_classes,
            scoring=CombatScoringConfig(),
        )
        assert scores == []

    def test_zero_samples(
        self,
        simple_roster: list[str],
        seeded_rng: random.Random,
        sample_classes: list[ClassDefinition],
    ) -> None:
        """Zero samples should return empty list."""
        scores = sample_unit_scores(
            roster=simple_roster,
            unit_size=3,
            samples=0,
            rng=seeded_rng,
            character_classes={},
            classes=sample_classes,
            scoring=CombatScoringConfig(),
        )
        assert scores == []

    def test_valid_sampling(
        self,
        simple_roster: list[str],
        sample_character_classes: dict[str, str],
        seeded_rng: random.Random,
        sample_classes: list[ClassDefinition],
    ) -> None:
        """Valid sampling should return correct number of scores."""
        scores = sample_unit_scores(
            roster=simple_roster,
            unit_size=3,
            samples=5,
            rng=seeded_rng,
            character_classes=sample_character_classes,
            classes=sample_classes,
            scoring=CombatScoringConfig(),
        )
        assert len(scores) == 5
        assert all(isinstance(s, float) for s in scores)

    def test_reproducible_with_seed(
        self,
        simple_roster: list[str],
        sample_character_classes: dict[str, str],
        sample_classes: list[ClassDefinition],
    ) -> None:
        """Same seed should produce same results."""
        rng1 = random.Random(42)
        rng2 = random.Random(42)

        scores1 = sample_unit_scores(
            roster=simple_roster,
            unit_size=3,
            samples=5,
            rng=rng1,
            character_classes=sample_character_classes,
            classes=sample_classes,
            scoring=CombatScoringConfig(),
        )
        scores2 = sample_unit_scores(
            roster=simple_roster,
            unit_size=3,
            samples=5,
            rng=rng2,
            character_classes=sample_character_classes,
            classes=sample_classes,
            scoring=CombatScoringConfig(),
        )
        assert scores1 == scores2


# --- Tests for generate_random_assignment ---


class TestGenerateRandomAssignment:
    """Tests for generate_random_assignment function."""

    def test_empty_units_raises(
        self, simple_roster: list[str], seeded_rng: random.Random
    ) -> None:
        """Empty units list should raise error."""
        with pytest.raises(SolveError, match="At least one unit size is required"):
            generate_random_assignment(
                roster=simple_roster,
                units=[],
                rapport_edges=set(),
                whitelist=set(),
                blacklist=set(),
                rng=seeded_rng,
            )

    def test_unit_size_less_than_two_raises(
        self, simple_roster: list[str], seeded_rng: random.Random
    ) -> None:
        """Unit size less than 2 should raise error."""
        with pytest.raises(SolveError, match="Unit sizes must be at least 2"):
            generate_random_assignment(
                roster=simple_roster,
                units=[1, 3],
                rapport_edges=set(),
                whitelist=set(),
                blacklist=set(),
                rng=seeded_rng,
            )

    def test_duplicate_roster_raises(self, seeded_rng: random.Random) -> None:
        """Duplicate roster entries should raise error."""
        with pytest.raises(SolveError, match="Roster contains duplicate character ids"):
            generate_random_assignment(
                roster=["alice", "bob", "alice"],
                units=[2],
                rapport_edges=set(),
                whitelist=set(),
                blacklist=set(),
                rng=seeded_rng,
            )

    def test_whitelist_blacklist_overlap_raises(
        self, simple_roster: list[str], seeded_rng: random.Random
    ) -> None:
        """Overlapping whitelist and blacklist should raise error."""
        pair = make_pair("alice", "bob")
        with pytest.raises(SolveError, match="Whitelist and blacklist overlap"):
            generate_random_assignment(
                roster=simple_roster,
                units=[3, 3],
                rapport_edges={pair},
                whitelist={pair},
                blacklist={pair},
                rng=seeded_rng,
            )

    def test_whitelist_missing_roster_raises(
        self, simple_roster: list[str], seeded_rng: random.Random
    ) -> None:
        """Whitelist with missing roster members should raise error."""
        pair = make_pair("alice", "missing")
        with pytest.raises(
            SolveError, match="Whitelist pair contains ids missing from roster"
        ):
            generate_random_assignment(
                roster=simple_roster,
                units=[3, 3],
                rapport_edges={pair},
                whitelist={pair},
                blacklist=set(),
                rng=seeded_rng,
            )

    def test_whitelist_not_rapport_raises(
        self, simple_roster: list[str], seeded_rng: random.Random
    ) -> None:
        """Whitelist pair not in rapport edges should raise error."""
        pair = make_pair("alice", "bob")
        with pytest.raises(SolveError, match="Whitelist pair is not a valid rapport"):
            generate_random_assignment(
                roster=simple_roster,
                units=[3, 3],
                rapport_edges=set(),  # empty - pair not in edges
                whitelist={pair},
                blacklist=set(),
                rng=seeded_rng,
            )

    def test_simple_assignment(self, seeded_rng: random.Random) -> None:
        """Simple assignment should return valid units."""
        roster = ["alice", "bob", "charlie", "dave"]
        result = generate_random_assignment(
            roster=roster,
            units=[2, 2],
            rapport_edges=set(),
            whitelist=set(),
            blacklist=set(),
            rng=seeded_rng,
        )
        assert result is not None
        assert len(result) == 2
        assert all(len(unit) == 2 for unit in result)
        # All roster members should be assigned
        all_assigned = {m for unit in result for m in unit}
        assert all_assigned == set(roster)

    def test_roster_smaller_than_slots(self, seeded_rng: random.Random) -> None:
        """Roster smaller than slots should still produce valid assignment.

        The function adds dummies to fill slots, but may also drop clusters
        to fit the exact slot count. This test just verifies the function
        produces a valid result without crashing.
        """
        roster = ["alice", "bob", "charlie", "dave", "eve"]
        result = generate_random_assignment(
            roster=roster,
            units=[3, 3],  # need 6 slots, only 5 roster
            rapport_edges=set(),
            whitelist=set(),
            blacklist=set(),
            rng=seeded_rng,
        )
        # Function should return a result (dummies depend on internal logic)
        assert result is not None
        assert len(result) == 2
        # Total assigned should match unit sizes
        total_assigned = sum(len(unit) for unit in result)
        # Should assign to fill the units as best as possible
        assert total_assigned >= 4  # At minimum some assignment happens

    def test_assignment_respects_blacklist(self, seeded_rng: random.Random) -> None:
        """Assignment should not place blacklisted pairs in same unit."""
        roster = ["alice", "bob", "charlie", "dave"]
        blacklist = {make_pair("alice", "bob")}

        # Try multiple times to ensure blacklist is respected
        for _ in range(10):
            result = generate_random_assignment(
                roster=roster,
                units=[2, 2],
                rapport_edges=set(),
                whitelist=set(),
                blacklist=blacklist,
                rng=seeded_rng,
            )
            if result is not None:
                for unit in result:
                    unit_set = set(unit)
                    # Alice and bob should not be in same unit
                    assert not ({"alice", "bob"}.issubset(unit_set))
                break


# --- Tests for _assign_clusters_randomly ---


class TestAssignClustersRandomly:
    """Tests for _assign_clusters_randomly function."""

    def test_empty_clusters(self, seeded_rng: random.Random) -> None:
        """Empty clusters should return empty assignments."""
        result = _assign_clusters_randomly(
            clusters=[],
            units=[3, 3],
            cluster_conflicts=[],
            rng=seeded_rng,
        )
        # Empty clusters means capacity doesn't match
        assert result is None or result == [[], []]

    def test_simple_assignment(self, seeded_rng: random.Random) -> None:
        """Simple clusters should be assigned to units."""
        clusters = [
            Cluster(members=("alice", "bob")),
            Cluster(members=("charlie", "dave")),
        ]
        conflicts = [[False, False], [False, False]]

        result = _assign_clusters_randomly(
            clusters=clusters,
            units=[2, 2],
            cluster_conflicts=conflicts,
            rng=seeded_rng,
        )
        assert result is not None
        assert len(result) == 2
        # Each unit should have exactly one cluster
        assert all(len(u) == 1 for u in result)

    def test_conflict_respected(self, seeded_rng: random.Random) -> None:
        """Conflicting clusters should not be in same unit."""
        clusters = [
            Cluster(members=("alice",)),
            Cluster(members=("bob",)),
            Cluster(members=("charlie",)),
        ]
        # Cluster 0 and 1 conflict
        conflicts = [
            [False, True, False],
            [True, False, False],
            [False, False, False],
        ]

        # With only one unit, can't fit conflicting clusters
        result = _assign_clusters_randomly(
            clusters=clusters,
            units=[3],
            cluster_conflicts=conflicts,
            rng=seeded_rng,
        )
        # Should fail because conflicting clusters can't be in same unit
        assert result is None

    def test_capacity_mismatch_returns_none(self, seeded_rng: random.Random) -> None:
        """When clusters don't fit exactly, should return None."""
        clusters = [
            Cluster(members=("alice", "bob", "charlie")),
        ]
        conflicts = [[False]]

        result = _assign_clusters_randomly(
            clusters=clusters,
            units=[2, 2],  # Need 4 slots, cluster has 3
            cluster_conflicts=conflicts,
            rng=seeded_rng,
        )
        assert result is None
