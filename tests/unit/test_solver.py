"""Unit tests for solver module."""

from __future__ import annotations

import pytest

from unicorn_armada.solver import Cluster, SolveError, UnionFind, UnitState, solve
from unicorn_armada.utils import pair_key


class TestCluster:
    """Tests for Cluster model."""

    def test_creates_cluster(self) -> None:
        """Cluster should store members as tuple."""
        cluster = Cluster(members=("alice", "bob"))
        assert cluster.members == ("alice", "bob")

    def test_size_property(self) -> None:
        """Cluster.size should return member count."""
        cluster = Cluster(members=("alice", "bob", "charlie"))
        assert cluster.size == 3

    def test_immutable(self) -> None:
        """Cluster should be immutable (frozen)."""
        from pydantic import ValidationError

        cluster = Cluster(members=("alice",))
        with pytest.raises(ValidationError):
            cluster.members = ("bob",)  # type: ignore


class TestUnitState:
    """Tests for UnitState model."""

    def test_creates_state(self) -> None:
        """UnitState should store capacity and clusters."""
        state = UnitState(capacity=4)
        assert state.capacity == 4
        assert state.clusters == []

    def test_clusters_mutable(self) -> None:
        """UnitState.clusters should be mutable."""
        state = UnitState(capacity=4)
        state.clusters.append(0)
        assert state.clusters == [0]


class TestUnionFind:
    """Tests for UnionFind class."""

    def test_find_returns_self_initially(self) -> None:
        """find should return item itself before any unions."""
        uf = UnionFind(["a", "b", "c"])
        assert uf.find("a") == "a"
        assert uf.find("b") == "b"

    def test_union_merges_sets(self) -> None:
        """union should merge two items into same set."""
        uf = UnionFind(["a", "b", "c"])
        uf.union("a", "b")
        assert uf.find("a") == uf.find("b")

    def test_union_is_transitive(self) -> None:
        """Chained unions should create single set."""
        uf = UnionFind(["a", "b", "c"])
        uf.union("a", "b")
        uf.union("b", "c")
        assert uf.find("a") == uf.find("c")

    def test_separate_sets_different_roots(self) -> None:
        """Unioned items in separate sets have different roots."""
        uf = UnionFind(["a", "b", "c", "d"])
        uf.union("a", "b")
        uf.union("c", "d")
        assert uf.find("a") != uf.find("c")


class TestSolve:
    """Tests for solve function."""

    def test_empty_units_raises(self) -> None:
        """solve with empty units should raise SolveError."""
        with pytest.raises(SolveError, match="At least one unit"):
            solve(
                roster=["alice", "bob"],
                units=[],
                rapport_edges=set(),
                whitelist=set(),
                blacklist=set(),
                seed=0,
                restarts=1,
                swap_iterations=1,
            )

    def test_unit_size_below_two_raises(self) -> None:
        """solve with unit size < 2 should raise SolveError."""
        with pytest.raises(SolveError, match="at least 2"):
            solve(
                roster=["alice", "bob"],
                units=[1],
                rapport_edges=set(),
                whitelist=set(),
                blacklist=set(),
                seed=0,
                restarts=1,
                swap_iterations=1,
            )

    def test_duplicate_roster_raises(self) -> None:
        """solve with duplicate roster entries should raise SolveError."""
        with pytest.raises(SolveError, match="duplicate"):
            solve(
                roster=["alice", "alice"],
                units=[2],
                rapport_edges=set(),
                whitelist=set(),
                blacklist=set(),
                seed=0,
                restarts=1,
                swap_iterations=1,
            )

    def test_overlapping_lists_raises(self) -> None:
        """solve with overlapping whitelist/blacklist should raise."""
        overlap = {pair_key("alice", "bob")}
        with pytest.raises(SolveError, match="overlap"):
            solve(
                roster=["alice", "bob", "charlie", "dave"],
                units=[2, 2],
                rapport_edges=set(),
                whitelist=overlap,
                blacklist=overlap,
                seed=0,
                restarts=1,
                swap_iterations=1,
            )

    def test_min_combat_without_fn_raises(self) -> None:
        """solve with min_combat_score but no fn should raise."""
        with pytest.raises(SolveError, match="combat data"):
            solve(
                roster=["alice", "bob"],
                units=[2],
                rapport_edges=set(),
                whitelist=set(),
                blacklist=set(),
                seed=0,
                restarts=1,
                swap_iterations=1,
                min_combat_score=10.0,
                combat_score_fn=None,
            )

    def test_negative_min_combat_raises(self) -> None:
        """solve with negative min_combat_score should raise."""
        with pytest.raises(SolveError, match="negative"):
            solve(
                roster=["alice", "bob"],
                units=[2],
                rapport_edges=set(),
                whitelist=set(),
                blacklist=set(),
                seed=0,
                restarts=1,
                swap_iterations=1,
                min_combat_score=-1.0,
                combat_score_fn=lambda x: 0.0,
            )

    def test_simple_solve(self) -> None:
        """solve should return valid solution for simple case."""
        roster = ["alice", "bob", "charlie", "dave"]
        edges = {pair_key("alice", "bob"), pair_key("charlie", "dave")}

        solution = solve(
            roster=roster,
            units=[2, 2],
            rapport_edges=edges,
            whitelist=set(),
            blacklist=set(),
            seed=42,
            restarts=5,
            swap_iterations=10,
        )

        assert len(solution.units) == 2
        assert all(len(unit) == 2 for unit in solution.units)
        assert solution.total_rapports >= 0

    def test_whitelist_enforced(self) -> None:
        """solve should put whitelisted pairs in same unit."""
        roster = ["alice", "bob", "charlie", "dave"]
        # Whitelist pair must also be in rapport_edges
        whitelist = {pair_key("alice", "bob")}
        edges = {pair_key("alice", "bob"), pair_key("charlie", "dave")}

        solution = solve(
            roster=roster,
            units=[2, 2],
            rapport_edges=edges,
            whitelist=whitelist,
            blacklist=set(),
            seed=42,
            restarts=5,
            swap_iterations=10,
        )

        # Alice and Bob must be in same unit
        alice_unit = next(i for i, u in enumerate(solution.units) if "alice" in u)
        bob_unit = next(i for i, u in enumerate(solution.units) if "bob" in u)
        assert alice_unit == bob_unit

    def test_blacklist_enforced(self) -> None:
        """solve should put blacklisted pairs in different units."""
        roster = ["alice", "bob", "charlie", "dave"]
        blacklist = {pair_key("alice", "bob")}

        solution = solve(
            roster=roster,
            units=[2, 2],
            rapport_edges=set(),
            whitelist=set(),
            blacklist=blacklist,
            seed=42,
            restarts=5,
            swap_iterations=10,
        )

        # Alice and Bob must be in different units
        alice_unit = next(i for i, u in enumerate(solution.units) if "alice" in u)
        bob_unit = next(i for i, u in enumerate(solution.units) if "bob" in u)
        assert alice_unit != bob_unit

    def test_deterministic_with_seed(self) -> None:
        """solve with same seed should produce same result."""
        roster = ["alice", "bob", "charlie", "dave", "eve", "frank"]
        edges = {pair_key("alice", "bob"), pair_key("charlie", "dave")}

        solution1 = solve(
            roster=roster,
            units=[3, 3],
            rapport_edges=edges,
            whitelist=set(),
            blacklist=set(),
            seed=12345,
            restarts=10,
            swap_iterations=20,
        )

        solution2 = solve(
            roster=roster,
            units=[3, 3],
            rapport_edges=edges,
            whitelist=set(),
            blacklist=set(),
            seed=12345,
            restarts=10,
            swap_iterations=20,
        )

        assert solution1.units == solution2.units
        assert solution1.total_rapports == solution2.total_rapports
