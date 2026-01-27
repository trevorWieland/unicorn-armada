"""Unit tests for io module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from unicorn_armada.io import (
    FileStorage,
    InputError,
    load_character_classes_csv,
    load_dataset,
    load_pairs_csv,
    load_roster_csv,
    load_units_json,
    parse_units_arg,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestParseUnitsArg:
    """Tests for parse_units_arg function."""

    def test_parses_comma_separated(self) -> None:
        """parse_units_arg should parse comma-separated integers."""
        result = parse_units_arg("3,4,5")
        assert result == [3, 4, 5]

    def test_strips_whitespace(self) -> None:
        """parse_units_arg should strip whitespace around values."""
        result = parse_units_arg(" 3 , 4 , 5 ")
        assert result == [3, 4, 5]

    def test_filters_empty_values(self) -> None:
        """parse_units_arg should filter empty values."""
        result = parse_units_arg("3,,4,5,")
        assert result == [3, 4, 5]

    def test_invalid_integer_raises(self) -> None:
        """parse_units_arg should raise InputError for non-integers."""
        with pytest.raises(InputError, match="Invalid unit size"):
            parse_units_arg("3,abc,5")

    def test_empty_input_raises(self) -> None:
        """parse_units_arg should raise InputError for empty input."""
        with pytest.raises(InputError, match="cannot be empty"):
            parse_units_arg("")


class TestLoadUnitsJson:
    """Tests for load_units_json function."""

    def test_loads_valid_json(self, tmp_path: Path) -> None:
        """load_units_json should load valid JSON array."""
        path = tmp_path / "units.json"
        path.write_text("[3, 4, 5]")
        result = load_units_json(path)
        assert result == [3, 4, 5]

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """load_units_json should raise InputError for missing file."""
        path = tmp_path / "missing.json"
        with pytest.raises(InputError, match="not found"):
            load_units_json(path)

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        """load_units_json should raise InputError for invalid JSON."""
        path = tmp_path / "units.json"
        path.write_text("not json")
        with pytest.raises(InputError, match="invalid"):
            load_units_json(path)

    def test_non_list_raises(self, tmp_path: Path) -> None:
        """load_units_json should raise InputError for non-list JSON."""
        path = tmp_path / "units.json"
        path.write_text('{"key": "value"}')
        with pytest.raises(InputError, match="list of integers"):
            load_units_json(path)


class TestLoadRosterCsv:
    """Tests for load_roster_csv function."""

    def test_loads_simple_roster(self, tmp_path: Path) -> None:
        """load_roster_csv should load simple roster."""
        path = tmp_path / "roster.csv"
        path.write_text("alice\nbob\ncharlie")
        result = load_roster_csv(path)
        assert result == ["alice", "bob", "charlie"]

    def test_loads_roster_with_header(self, tmp_path: Path) -> None:
        """load_roster_csv should skip header row."""
        path = tmp_path / "roster.csv"
        path.write_text("id\nalice\nbob")
        result = load_roster_csv(path)
        assert result == ["alice", "bob"]

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        """load_roster_csv should strip whitespace."""
        path = tmp_path / "roster.csv"
        path.write_text("  alice  \n  bob  ")
        result = load_roster_csv(path)
        assert result == ["alice", "bob"]

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """load_roster_csv should raise InputError for missing file."""
        path = tmp_path / "missing.csv"
        with pytest.raises(InputError, match="not found"):
            load_roster_csv(path)


class TestLoadPairsCsv:
    """Tests for load_pairs_csv function."""

    def test_loads_simple_pairs(self, tmp_path: Path) -> None:
        """load_pairs_csv should load simple pairs."""
        path = tmp_path / "pairs.csv"
        path.write_text("alice,bob\ncharlie,dave")
        result = load_pairs_csv(path)
        assert frozenset({"alice", "bob"}) in result
        assert frozenset({"charlie", "dave"}) in result

    def test_loads_pairs_with_header(self, tmp_path: Path) -> None:
        """load_pairs_csv should skip header row."""
        path = tmp_path / "pairs.csv"
        path.write_text("a,b\nalice,bob")
        result = load_pairs_csv(path)
        assert frozenset({"alice", "bob"}) in result
        assert len(result) == 1

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """load_pairs_csv should raise InputError for missing file."""
        path = tmp_path / "missing.csv"
        with pytest.raises(InputError, match="not found"):
            load_pairs_csv(path)


class TestLoadCharacterClassesCsv:
    """Tests for load_character_classes_csv function."""

    def test_loads_simple_mapping(self, tmp_path: Path) -> None:
        """load_character_classes_csv should load class mapping."""
        path = tmp_path / "classes.csv"
        path.write_text("alice,warrior\nbob,mage")
        result = load_character_classes_csv(path)
        assert result["alice"] == "warrior"
        assert result["bob"] == "mage"

    def test_loads_mapping_with_header(self, tmp_path: Path) -> None:
        """load_character_classes_csv should skip header row."""
        path = tmp_path / "classes.csv"
        path.write_text("id,class\nalice,warrior")
        result = load_character_classes_csv(path)
        assert result["alice"] == "warrior"
        assert len(result) == 1

    def test_conflicting_entries_raises(self, tmp_path: Path) -> None:
        """load_character_classes_csv should raise for conflicts."""
        path = tmp_path / "classes.csv"
        path.write_text("alice,warrior\nalice,mage")
        with pytest.raises(InputError, match="conflicting"):
            load_character_classes_csv(path)


class TestLoadDataset:
    """Tests for load_dataset function."""

    def test_loads_valid_dataset(self, tmp_path: Path) -> None:
        """load_dataset should load valid dataset JSON."""
        path = tmp_path / "dataset.json"
        data = {
            "characters": [{"id": "alice"}, {"id": "bob"}],
            "rapports": [{"id": "alice", "pairs": ["bob"]}],
        }
        path.write_text(json.dumps(data))
        result = load_dataset(path)
        assert len(result.characters) == 2
        assert result.characters[0].id == "alice"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """load_dataset should raise InputError for missing file."""
        path = tmp_path / "missing.json"
        with pytest.raises(InputError, match="not found"):
            load_dataset(path)

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        """load_dataset should raise InputError for invalid JSON."""
        path = tmp_path / "dataset.json"
        path.write_text("not json")
        with pytest.raises(InputError, match="invalid"):
            load_dataset(path)


class TestFileStorage:
    """Tests for FileStorage class."""

    def test_implements_storage_protocol(self) -> None:
        """FileStorage should implement StorageProtocol."""
        storage = FileStorage()
        assert hasattr(storage, "load_dataset")
        assert hasattr(storage, "load_roster")
        assert hasattr(storage, "load_pairs")
        assert hasattr(storage, "load_units")
        assert hasattr(storage, "load_scoring")
        assert hasattr(storage, "load_character_classes")
        assert hasattr(storage, "write_json")
        assert hasattr(storage, "write_text")

    def test_write_json(self, tmp_path: Path) -> None:
        """FileStorage.write_json should write JSON content."""
        storage = FileStorage()
        path = tmp_path / "output.json"
        storage.write_json(path, '{"key": "value"}')
        assert path.read_text() == '{"key": "value"}'

    def test_write_text(self, tmp_path: Path) -> None:
        """FileStorage.write_text should write text content."""
        storage = FileStorage()
        path = tmp_path / "output.txt"
        storage.write_text(path, "hello world")
        assert path.read_text() == "hello world"
