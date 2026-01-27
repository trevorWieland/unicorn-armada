"""Unit tests for utils module."""

from __future__ import annotations

import pytest

from unicorn_armada.utils import normalize_id, normalize_ids, normalize_tag, pair_key


class TestNormalizeId:
    """Tests for normalize_id function."""

    def test_strips_whitespace(self) -> None:
        """normalize_id should strip leading/trailing whitespace."""
        assert normalize_id("  alice  ") == "alice"

    def test_preserves_case(self) -> None:
        """normalize_id should preserve original case."""
        assert normalize_id("Alice") == "Alice"

    def test_empty_string_stays_empty(self) -> None:
        """normalize_id on whitespace-only returns empty string."""
        assert normalize_id("   ") == ""

    def test_no_whitespace_unchanged(self) -> None:
        """normalize_id on clean string returns same string."""
        assert normalize_id("bob") == "bob"


class TestNormalizeTag:
    """Tests for normalize_tag function."""

    def test_strips_whitespace(self) -> None:
        """normalize_tag should strip leading/trailing whitespace."""
        assert normalize_tag("  warrior  ") == "warrior"

    def test_lowercases(self) -> None:
        """normalize_tag should lowercase the value."""
        assert normalize_tag("Warrior") == "warrior"

    def test_strips_and_lowercases(self) -> None:
        """normalize_tag should strip and lowercase."""
        assert normalize_tag("  MAGE  ") == "mage"

    def test_empty_string_stays_empty(self) -> None:
        """normalize_tag on whitespace-only returns empty string."""
        assert normalize_tag("   ") == ""


class TestPairKey:
    """Tests for pair_key function."""

    def test_creates_frozenset(self) -> None:
        """pair_key should return a frozenset of two ids."""
        result = pair_key("alice", "bob")
        assert isinstance(result, frozenset)
        assert result == frozenset({"alice", "bob"})

    def test_order_independent(self) -> None:
        """pair_key should produce same result regardless of order."""
        assert pair_key("alice", "bob") == pair_key("bob", "alice")

    def test_identical_ids_raises(self) -> None:
        """pair_key should raise ValueError for identical ids."""
        with pytest.raises(ValueError, match="identical"):
            pair_key("alice", "alice")


class TestNormalizeIds:
    """Tests for normalize_ids function."""

    def test_strips_all_ids(self) -> None:
        """normalize_ids should strip whitespace from all ids."""
        result = normalize_ids(["  alice  ", "bob  ", "  charlie"])
        assert result == ["alice", "bob", "charlie"]

    def test_filters_empty_strings(self) -> None:
        """normalize_ids should filter out empty/whitespace-only strings."""
        result = normalize_ids(["alice", "", "  ", "bob"])
        assert result == ["alice", "bob"]

    def test_empty_input_returns_empty(self) -> None:
        """normalize_ids on empty input returns empty list."""
        assert normalize_ids([]) == []

    def test_preserves_order(self) -> None:
        """normalize_ids should preserve order of valid ids."""
        result = normalize_ids(["charlie", "alice", "bob"])
        assert result == ["charlie", "alice", "bob"]
