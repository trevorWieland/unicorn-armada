"""Unit tests for scoring module."""

from __future__ import annotations

from unicorn_armada.scoring import rapport_pairs_in_unit, score_unit
from unicorn_armada.utils import pair_key


class TestRapportPairsInUnit:
    """Tests for rapport_pairs_in_unit function."""

    def test_finds_pairs_in_unit(self) -> None:
        """rapport_pairs_in_unit should find rapport pairs."""
        edges = {pair_key("alice", "bob"), pair_key("bob", "charlie")}
        unit = ["alice", "bob", "charlie"]

        pairs = rapport_pairs_in_unit(unit, edges)

        assert len(pairs) == 2
        assert ("alice", "bob") in pairs
        assert ("bob", "charlie") in pairs

    def test_empty_unit(self) -> None:
        """rapport_pairs_in_unit with empty unit returns empty."""
        edges = {pair_key("alice", "bob")}

        pairs = rapport_pairs_in_unit([], edges)

        assert pairs == []

    def test_no_rapport_edges(self) -> None:
        """rapport_pairs_in_unit with no edges returns empty."""
        unit = ["alice", "bob", "charlie"]

        pairs = rapport_pairs_in_unit(unit, set())

        assert pairs == []

    def test_single_member_unit(self) -> None:
        """rapport_pairs_in_unit with single member returns empty."""
        edges = {pair_key("alice", "bob")}

        pairs = rapport_pairs_in_unit(["alice"], edges)

        assert pairs == []

    def test_no_matching_pairs(self) -> None:
        """rapport_pairs_in_unit with no matching pairs returns empty."""
        edges = {pair_key("dave", "eve")}
        unit = ["alice", "bob", "charlie"]

        pairs = rapport_pairs_in_unit(unit, edges)

        assert pairs == []


class TestScoreUnit:
    """Tests for score_unit function."""

    def test_counts_rapport_pairs(self) -> None:
        """score_unit should count rapport pairs."""
        edges = {pair_key("alice", "bob"), pair_key("bob", "charlie")}
        unit = ["alice", "bob", "charlie"]

        score = score_unit(unit, edges)

        assert score == 2

    def test_empty_unit_scores_zero(self) -> None:
        """score_unit with empty unit returns 0."""
        edges = {pair_key("alice", "bob")}

        score = score_unit([], edges)

        assert score == 0

    def test_no_edges_scores_zero(self) -> None:
        """score_unit with no edges returns 0."""
        unit = ["alice", "bob", "charlie"]

        score = score_unit(unit, set())

        assert score == 0

    def test_full_clique_scores_max(self) -> None:
        """score_unit with full clique scores n*(n-1)/2."""
        # All pairs have rapport
        edges = {
            pair_key("alice", "bob"),
            pair_key("alice", "charlie"),
            pair_key("bob", "charlie"),
        }
        unit = ["alice", "bob", "charlie"]

        score = score_unit(unit, edges)

        # 3 members = 3 pairs possible
        assert score == 3
