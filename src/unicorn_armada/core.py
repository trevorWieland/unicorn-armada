"""Core business logic for unicorn-armada.

This module contains the core domain logic that is independent of any surface layer
(CLI, TUI, API). Surface layers should delegate to functions here rather than
containing business logic themselves.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from .combat import compute_combat_summary
from .io import (
    load_character_classes_csv,
    load_combat_scoring_json,
    load_dataset,
    load_pairs_csv,
    load_roster_csv,
    load_units_json,
    parse_units_arg,
)
from .models import CombatScoringConfig, Dataset
from .utils import Pair, pair_key

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class ValidationError(ValueError):
    """Error raised when input validation fails."""


class ProblemInputs:
    """Container for validated problem inputs."""

    def __init__(
        self,
        dataset: Dataset,
        roster_ids: list[str],
        unit_sizes: list[int],
        rapport_edges: set[Pair],
        whitelist_pairs: set[Pair],
        blacklist_pairs: set[Pair],
    ) -> None:
        self.dataset = dataset
        self.roster_ids = roster_ids
        self.unit_sizes = unit_sizes
        self.rapport_edges = rapport_edges
        self.whitelist_pairs = whitelist_pairs
        self.blacklist_pairs = blacklist_pairs

    @property
    def roster_set(self) -> set[str]:
        return set(self.roster_ids)

    @property
    def character_set(self) -> set[str]:
        return {c.id for c in self.dataset.characters}


class CombatContext:
    """Container for combat scoring context."""

    def __init__(
        self,
        scoring: CombatScoringConfig,
        effective_classes: dict[str, str],
    ) -> None:
        self.scoring = scoring
        self.effective_classes = effective_classes


def load_and_validate_problem(
    dataset_path: Path,
    roster_path: Path | None,
    units_str: str | None,
    units_file_path: Path | None,
    whitelist_path: Path | None,
    blacklist_path: Path | None,
    default_roster_path: Path | None = None,
    default_whitelist_path: Path | None = None,
    default_blacklist_path: Path | None = None,
) -> ProblemInputs:
    """Load and validate all problem inputs.

    Args:
        dataset_path: Path to the dataset JSON file.
        roster_path: Path to roster CSV, or None to use default.
        units_str: Comma-separated unit sizes, or None.
        units_file_path: Path to units JSON file, or None.
        whitelist_path: Path to whitelist CSV, or None to use default.
        blacklist_path: Path to blacklist CSV, or None to use default.
        default_roster_path: Default roster path to use if roster_path is None.
        default_whitelist_path: Default whitelist path to use if whitelist_path is None.
        default_blacklist_path: Default blacklist path to use if blacklist_path is None.

    Returns:
        Validated ProblemInputs container.

    Raises:
        ValidationError: If inputs fail validation.
        InputError: If files cannot be read or parsed.
    """
    # Load dataset
    dataset_data = load_dataset(dataset_path)

    character_ids = [character.id for character in dataset_data.characters]
    character_set = set(character_ids)
    if len(character_ids) != len(character_set):
        raise ValidationError("Dataset contains duplicate character ids")

    # Load roster
    roster_ids: list[str]
    if roster_path is None and default_roster_path is not None:
        if default_roster_path.exists():
            roster_ids = load_roster_csv(default_roster_path)
        else:
            roster_ids = sorted(character_set)
    elif roster_path is not None:
        roster_ids = load_roster_csv(roster_path)
    else:
        roster_ids = sorted(character_set)

    roster_set = set(roster_ids)
    if len(roster_ids) != len(roster_set):
        raise ValidationError("Roster contains duplicate character ids")
    unknown = roster_set - character_set
    if unknown:
        raise ValidationError(
            f"Roster contains unknown ids: {', '.join(sorted(unknown))}"
        )

    # Load unit sizes
    if units_file_path is not None and units_str is not None:
        raise ValidationError("Provide either units or units_file, not both")
    if units_file_path is None and units_str is None:
        raise ValidationError("Provide either units or units_file")

    unit_sizes: list[int]
    if units_file_path is not None:
        unit_sizes = load_units_json(units_file_path)
    else:
        unit_sizes = parse_units_arg(units_str or "")

    # Build rapport edges
    rapport_edges: set[Pair] = set()
    for entry in dataset_data.rapports:
        if entry.id not in character_set:
            continue
        for partner in entry.pairs:
            if partner not in character_set:
                continue
            rapport_edges.add(pair_key(entry.id, partner))
    rapport_edges = {pair for pair in rapport_edges if pair.issubset(roster_set)}

    # Load whitelist
    whitelist_pairs: set[Pair]
    if whitelist_path is None and default_whitelist_path is not None:
        if default_whitelist_path.exists():
            whitelist_pairs = load_pairs_csv(default_whitelist_path)
        else:
            whitelist_pairs = set()
    elif whitelist_path is not None:
        whitelist_pairs = load_pairs_csv(whitelist_path)
    else:
        whitelist_pairs = set()

    # Load blacklist
    blacklist_pairs: set[Pair]
    if blacklist_path is None and default_blacklist_path is not None:
        if default_blacklist_path.exists():
            blacklist_pairs = load_pairs_csv(default_blacklist_path)
        else:
            blacklist_pairs = set()
    elif blacklist_path is not None:
        blacklist_pairs = load_pairs_csv(blacklist_path)
    else:
        blacklist_pairs = set()

    # Validate whitelist
    invalid_whitelist = {
        pair for pair in whitelist_pairs if not pair.issubset(roster_set)
    }
    if invalid_whitelist:
        raise ValidationError("Whitelist pair contains missing roster ids")

    invalid_rapports = {pair for pair in whitelist_pairs if pair not in rapport_edges}
    if invalid_rapports:
        raise ValidationError("Whitelist pair is not a valid rapport")

    # Filter blacklist (warn, don't error)
    blacklist_pairs = {pair for pair in blacklist_pairs if pair.issubset(roster_set)}

    return ProblemInputs(
        dataset=dataset_data,
        roster_ids=roster_ids,
        unit_sizes=unit_sizes,
        rapport_edges=rapport_edges,
        whitelist_pairs=whitelist_pairs,
        blacklist_pairs=blacklist_pairs,
    )


def load_combat_context(
    dataset: Dataset,
    roster_set: set[str],
    combat_scoring_path: Path | None = None,
    character_classes_path: Path | None = None,
) -> CombatContext:
    """Load combat scoring context.

    Args:
        dataset: The loaded dataset.
        roster_set: Set of character IDs in the roster.
        combat_scoring_path: Path to combat scoring config, or None.
        character_classes_path: Path to class overrides CSV, or None.

    Returns:
        CombatContext with scoring config and effective classes.

    Raises:
        ValidationError: If validation fails.
        InputError: If files cannot be read.
    """
    from .combat import build_class_index

    combat_scoring = CombatScoringConfig()
    if combat_scoring_path is not None and combat_scoring_path.exists():
        combat_scoring = load_combat_scoring_json(combat_scoring_path)

    overrides: dict[str, str] = {}
    if character_classes_path is not None and character_classes_path.exists():
        overrides = load_character_classes_csv(character_classes_path)

    character_set = {character.id for character in dataset.characters}
    unknown_override_characters = set(overrides) - character_set
    if unknown_override_characters:
        formatted = ", ".join(sorted(unknown_override_characters))
        raise ValidationError(
            f"Character class overrides contain unknown ids: {formatted}"
        )

    class_index = build_class_index(dataset.classes)
    class_lines = {line.id: line for line in dataset.class_lines}
    default_classes = {
        character_id: info.default_class
        for character_id, info in dataset.character_classes.items()
    }

    override_class_ids = set(overrides.values())
    unknown_override_classes = {
        class_id for class_id in override_class_ids if class_id not in class_index
    }
    if unknown_override_classes:
        formatted = ", ".join(sorted(unknown_override_classes))
        raise ValidationError(
            f"Character class overrides reference unknown classes: {formatted}"
        )

    for character_id, class_id in overrides.items():
        info = dataset.character_classes.get(character_id)
        if info is None:
            raise ValidationError(
                f"Character {character_id} has no default class in dataset"
            )
        if info.class_line is None:
            if class_id != info.default_class:
                raise ValidationError(
                    f"Character {character_id} override {class_id} is not allowed; "
                    "no class line is defined."
                )
            continue
        line = class_lines.get(info.class_line)
        if line is None:
            raise ValidationError(
                f"Character {character_id} references unknown class line "
                f"{info.class_line}"
            )
        if class_id not in line.classes:
            raise ValidationError(
                f"Character {character_id} override {class_id} is not part of class "
                f"line {info.class_line}"
            )

    effective_classes = dict(default_classes)
    effective_classes.update(overrides)

    return CombatContext(
        scoring=combat_scoring,
        effective_classes=effective_classes,
    )


# Preset configurations
SCORING_PRESETS: dict[str, dict] = {
    "balanced": {
        "coverage": {
            "assist_type_weights": {"ranged": 0.5, "magick": 0.5, "healing": 0.5},
            "unit_type_weights": {"infantry": 0.3, "cavalry": 0.3, "flying": 0.3},
        },
        "diversity": {
            "unique_leader_bonus": 1.0,
            "duplicate_leader_penalty": 0.5,
            "mode": "class",
        },
    },
    "offensive": {
        "coverage": {
            "assist_type_weights": {"ranged": 1.0, "magick": 0.8, "healing": 0.3},
            "unit_type_weights": {"flying": 0.8, "cavalry": 0.6, "infantry": 0.2},
        },
        "diversity": {"unique_leader_bonus": 0.8, "duplicate_leader_penalty": 0.3},
    },
    "defensive": {
        "coverage": {
            "assist_type_weights": {"ranged": 0.3, "magick": 0.3, "healing": 1.0},
            "unit_type_weights": {"infantry": 0.8, "cavalry": 0.4, "flying": 0.4},
        },
        "diversity": {"unique_leader_bonus": 1.2, "duplicate_leader_penalty": 0.7},
    },
    "magic-heavy": {
        "coverage": {
            "assist_type_weights": {"ranged": 0.5, "magick": 1.0, "healing": 0.8},
            "unit_type_weights": {"infantry": 0.5, "cavalry": 0.4, "flying": 0.6},
        },
        "diversity": {
            "unique_leader_bonus": 0.8,
            "duplicate_leader_penalty": 0.3,
            "mode": "class",
        },
    },
}


def apply_preset(scoring: CombatScoringConfig, preset: str) -> CombatScoringConfig:
    """Apply a preset configuration to combat scoring.

    Args:
        scoring: Base scoring configuration.
        preset: Name of the preset to apply.

    Returns:
        New scoring configuration with preset values applied.

    Raises:
        ValidationError: If preset name is not recognized.
    """
    if preset not in SCORING_PRESETS:
        raise ValidationError(
            f"Unknown preset: {preset}. Available: {', '.join(SCORING_PRESETS.keys())}"
        )

    preset_config = SCORING_PRESETS[preset]
    updated = deepcopy(scoring)

    for key, value in preset_config.get("coverage", {}).items():
        setattr(updated.coverage, key, value)
    for key, value in preset_config.get("diversity", {}).items():
        if hasattr(updated.diversity, key):
            setattr(updated.diversity, key, value)

    return updated


def make_combat_score_fn(
    dataset: Dataset,
    effective_classes: dict[str, str],
    scoring: CombatScoringConfig,
) -> Callable[[list[list[str]]], float] | None:
    """Create a combat scoring function if data is available.

    Args:
        dataset: The loaded dataset.
        effective_classes: Mapping of character ID to class ID.
        scoring: Combat scoring configuration.

    Returns:
        A function that scores unit compositions, or None if data is unavailable.
    """
    if not dataset.classes or not effective_classes:
        return None

    def score_fn(units: list[list[str]]) -> float:
        return compute_combat_summary(
            units,
            effective_classes,
            dataset.classes,
            scoring,
        ).total_score

    return score_fn
