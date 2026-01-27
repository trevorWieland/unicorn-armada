"""Unit tests for models module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unicorn_armada.models import (
    Character,
    CharacterClassInfo,
    ClassDefinition,
    ClassLine,
    CombatScoringConfig,
    CoverageWeights,
    Dataset,
    DiversityWeights,
    RapportListEntry,
)


class TestCharacter:
    """Tests for Character model."""

    def test_valid_character(self) -> None:
        """Character with valid id should be created."""
        char = Character(id="alice")
        assert char.id == "alice"
        assert char.name is None

    def test_character_with_name(self) -> None:
        """Character with name should store it."""
        char = Character(id="alice", name="Alice")
        assert char.name == "Alice"

    def test_id_stripped(self) -> None:
        """Character id should be stripped of whitespace."""
        char = Character(id="  alice  ")
        assert char.id == "alice"

    def test_empty_id_fails(self) -> None:
        """Character with empty id should fail validation."""
        with pytest.raises(ValidationError):
            Character(id="")


class TestRapportListEntry:
    """Tests for RapportListEntry model."""

    def test_valid_entry(self) -> None:
        """RapportListEntry with valid data should be created."""
        entry = RapportListEntry(id="alice", pairs=["bob", "charlie"])
        assert entry.id == "alice"
        assert entry.pairs == ["bob", "charlie"]

    def test_default_pairs(self) -> None:
        """RapportListEntry without pairs should default to empty list."""
        entry = RapportListEntry(id="alice")
        assert entry.pairs == []

    def test_pairs_stripped(self) -> None:
        """Pair ids should be stripped of whitespace."""
        entry = RapportListEntry(id="alice", pairs=["  bob  ", "charlie  "])
        assert entry.pairs == ["bob", "charlie"]

    def test_duplicate_pairs_removed(self) -> None:
        """Duplicate pairs should be removed."""
        entry = RapportListEntry(id="alice", pairs=["bob", "bob", "charlie"])
        assert entry.pairs == ["bob", "charlie"]

    def test_self_in_pairs_fails(self) -> None:
        """RapportListEntry with self in pairs should fail."""
        with pytest.raises(ValidationError, match="cannot include self"):
            RapportListEntry(id="alice", pairs=["alice", "bob"])


class TestClassDefinition:
    """Tests for ClassDefinition model."""

    def test_valid_class(self) -> None:
        """ClassDefinition with valid data should be created."""
        cls = ClassDefinition(
            id="warrior",
            roles=["tank"],
            class_types=["melee"],
            unit_type="infantry",
            assist_type="none",
            stamina=100,
            mobility=3,
        )
        assert cls.id == "warrior"
        assert cls.roles == ["tank"]
        assert cls.row_preference == "flex"  # default

    def test_id_normalized(self) -> None:
        """Class id should be lowercased and stripped."""
        cls = ClassDefinition(
            id="  WARRIOR  ",
            roles=["tank"],
            class_types=["melee"],
            unit_type="infantry",
            assist_type="none",
            stamina=100,
            mobility=3,
        )
        assert cls.id == "warrior"

    def test_id_with_spaces_fails(self) -> None:
        """Class id with spaces should fail validation."""
        with pytest.raises(ValidationError, match="underscores"):
            ClassDefinition(
                id="war rior",
                roles=["tank"],
                class_types=["melee"],
                unit_type="infantry",
                assist_type="none",
                stamina=100,
                mobility=3,
            )

    def test_empty_roles_fails(self) -> None:
        """ClassDefinition with empty roles should fail."""
        with pytest.raises(ValidationError, match="at least one"):
            ClassDefinition(
                id="warrior",
                roles=[],
                class_types=["melee"],
                unit_type="infantry",
                assist_type="none",
                stamina=100,
                mobility=3,
            )


class TestClassLine:
    """Tests for ClassLine model."""

    def test_valid_class_line(self) -> None:
        """ClassLine with valid data should be created."""
        line = ClassLine(id="knight_line", classes=["squire", "knight"])
        assert line.id == "knight_line"
        assert line.classes == ["squire", "knight"]

    def test_empty_classes_fails(self) -> None:
        """ClassLine with empty classes should fail."""
        with pytest.raises(ValidationError, match="at least one"):
            ClassLine(id="knight_line", classes=[])


class TestCharacterClassInfo:
    """Tests for CharacterClassInfo model."""

    def test_valid_info(self) -> None:
        """CharacterClassInfo with valid data should be created."""
        info = CharacterClassInfo(default_class="warrior")
        assert info.default_class == "warrior"
        assert info.class_line is None

    def test_with_class_line(self) -> None:
        """CharacterClassInfo with class_line should store it."""
        info = CharacterClassInfo(default_class="warrior", class_line="knight_line")
        assert info.class_line == "knight_line"


class TestCoverageWeights:
    """Tests for CoverageWeights model."""

    def test_defaults(self) -> None:
        """CoverageWeights should have sensible defaults."""
        weights = CoverageWeights()
        assert weights.enabled is True
        assert "ranged" in weights.assist_type_weights
        assert "infantry" in weights.unit_type_weights


class TestDiversityWeights:
    """Tests for DiversityWeights model."""

    def test_defaults(self) -> None:
        """DiversityWeights should have sensible defaults."""
        weights = DiversityWeights()
        assert weights.enabled is True
        assert weights.mode == "class"


class TestCombatScoringConfig:
    """Tests for CombatScoringConfig model."""

    def test_defaults(self) -> None:
        """CombatScoringConfig should have sensible defaults."""
        config = CombatScoringConfig()
        assert config.role_weights == {}
        assert config.capability_weights == {}
        assert config.coverage.enabled is True
        assert config.diversity.enabled is True

    def test_role_weights_normalized(self) -> None:
        """Role weights should be normalized."""
        config = CombatScoringConfig(role_weights={"  TANK  ": 1.0})
        assert config.role_weights == {"tank": 1.0}


class TestDataset:
    """Tests for Dataset model."""

    def test_minimal_dataset(self) -> None:
        """Dataset with minimal data should be created."""
        ds = Dataset(
            characters=[Character(id="alice")],
            rapports=[RapportListEntry(id="alice")],
        )
        assert len(ds.characters) == 1
        assert len(ds.rapports) == 1

    def test_duplicate_class_ids_fails(self) -> None:
        """Dataset with duplicate class ids should fail."""
        with pytest.raises(ValidationError, match="duplicate"):
            Dataset(
                characters=[Character(id="alice")],
                rapports=[],
                classes=[
                    ClassDefinition(
                        id="warrior",
                        roles=["tank"],
                        class_types=["melee"],
                        unit_type="infantry",
                        assist_type="none",
                        stamina=100,
                        mobility=3,
                    ),
                    ClassDefinition(
                        id="warrior",  # duplicate
                        roles=["dps"],
                        class_types=["melee"],
                        unit_type="infantry",
                        assist_type="none",
                        stamina=80,
                        mobility=4,
                    ),
                ],
            )
