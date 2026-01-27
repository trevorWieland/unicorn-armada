"""Protocol interfaces for IO and storage operations.

This module defines protocol interfaces that abstract infrastructure concerns
(file I/O, storage, etc.) from the core domain. Implementations can be injected
to enable testing with mocks and swapping implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from .models import CombatScoringConfig, Dataset
    from .utils import Pair


class DatasetLoaderProtocol(Protocol):
    """Protocol for loading dataset files."""

    def load_dataset(self, path: Path) -> Dataset:
        """Load and validate a dataset from the given path.

        Args:
            path: Path to the dataset JSON file.

        Returns:
            Validated Dataset object.

        Raises:
            InputError: If the file cannot be read or validated.
        """
        ...


class RosterLoaderProtocol(Protocol):
    """Protocol for loading roster files."""

    def load_roster(self, path: Path) -> list[str]:
        """Load roster character IDs from the given path.

        Args:
            path: Path to the roster CSV file.

        Returns:
            List of character IDs.

        Raises:
            InputError: If the file cannot be read.
        """
        ...


class PairsLoaderProtocol(Protocol):
    """Protocol for loading pair files (whitelist/blacklist)."""

    def load_pairs(self, path: Path) -> set[Pair]:
        """Load character pairs from the given path.

        Args:
            path: Path to the pairs CSV file.

        Returns:
            Set of character ID pairs.

        Raises:
            InputError: If the file cannot be read.
        """
        ...


class UnitsLoaderProtocol(Protocol):
    """Protocol for loading unit size configurations."""

    def load_units(self, path: Path) -> list[int]:
        """Load unit sizes from the given path.

        Args:
            path: Path to the units JSON file.

        Returns:
            List of unit sizes.

        Raises:
            InputError: If the file cannot be read.
        """
        ...


class CombatScoringLoaderProtocol(Protocol):
    """Protocol for loading combat scoring configuration."""

    def load_scoring(self, path: Path) -> CombatScoringConfig:
        """Load combat scoring configuration from the given path.

        Args:
            path: Path to the combat scoring JSON file.

        Returns:
            Combat scoring configuration.

        Raises:
            InputError: If the file cannot be read.
        """
        ...


class CharacterClassesLoaderProtocol(Protocol):
    """Protocol for loading character class overrides."""

    def load_character_classes(self, path: Path) -> dict[str, str]:
        """Load character class overrides from the given path.

        Args:
            path: Path to the character classes CSV file.

        Returns:
            Mapping of character ID to class ID.

        Raises:
            InputError: If the file cannot be read.
        """
        ...


class OutputWriterProtocol(Protocol):
    """Protocol for writing output files."""

    def write_json(self, path: Path, data: str) -> None:
        """Write JSON content to the given path.

        Args:
            path: Path to write to.
            data: JSON string to write.
        """
        ...

    def write_text(self, path: Path, content: str) -> None:
        """Write text content to the given path.

        Args:
            path: Path to write to.
            content: Text content to write.
        """
        ...


class StorageProtocol(Protocol):
    """Combined protocol for all storage operations.

    This is a facade that combines all loader and writer protocols
    for convenience when a single storage interface is needed.
    """

    def load_dataset(self, path: Path) -> Dataset:
        """Load dataset from path."""
        ...

    def load_roster(self, path: Path) -> list[str]:
        """Load roster from path."""
        ...

    def load_pairs(self, path: Path) -> set[Pair]:
        """Load pairs from path."""
        ...

    def load_units(self, path: Path) -> list[int]:
        """Load units from path."""
        ...

    def load_scoring(self, path: Path) -> CombatScoringConfig:
        """Load combat scoring config from path."""
        ...

    def load_character_classes(self, path: Path) -> dict[str, str]:
        """Load character class overrides from path."""
        ...

    def write_json(self, path: Path, data: str) -> None:
        """Write JSON to path."""
        ...

    def write_text(self, path: Path, content: str) -> None:
        """Write text to path."""
        ...
