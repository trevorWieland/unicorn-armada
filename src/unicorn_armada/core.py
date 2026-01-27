"""Core business logic for unicorn-armada.

This module contains the core domain logic that is independent of any surface layer
(CLI, TUI, API). Surface layers should delegate to functions here rather than
containing business logic themselves.
"""

from __future__ import annotations

import random
from copy import deepcopy
from typing import TYPE_CHECKING, cast

from .benchmark import (
    BenchmarkStats,
    compute_stats,
    generate_random_assignment,
    sample_unit_scores,
)
from .combat import (
    build_class_index,
    compute_combat_summary,
    missing_default_classes_diagnostic,
)
from .io import parse_units_arg
from .models import (
    BenchmarkInputSummary,
    BenchmarkReport,
    BenchmarkRunResult,
    BenchmarkSampleCounts,
    BenchmarkStatsSummary,
    CombatDiagnostic,
    CombatScoringConfig,
    Dataset,
    RapportListEntry,
    RapportSyncResult,
    RapportSyncStats,
    SolveRunResult,
    UnitSizeReport,
    UserMessage,
)
from .solver import SolveError, solve
from .utils import Pair, normalize_id, pair_key

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from .protocols import StorageProtocol


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


def _format_pair(pair: Pair) -> str:
    left, right = sorted(pair)
    return f"{left},{right}"


def _sort_pairs(pairs: set[Pair]) -> list[Pair]:
    return sorted(pairs, key=lambda pair: tuple(sorted(pair)))


def load_and_validate_problem(
    storage: StorageProtocol,
    dataset_path: Path,
    roster_path: Path | None,
    units_str: str | None,
    units_file_path: Path | None,
    whitelist_path: Path | None,
    blacklist_path: Path | None,
    default_roster_path: Path | None = None,
    default_whitelist_path: Path | None = None,
    default_blacklist_path: Path | None = None,
) -> tuple[ProblemInputs, list[UserMessage]]:
    """Load and validate all problem inputs.

    Args:
        storage: Storage adapter for input loading.
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
        Tuple of validated ProblemInputs and warning messages.

    Raises:
        ValidationError: If inputs fail validation.
        InputError: If files cannot be read or parsed.
    """
    warnings: list[UserMessage] = []

    # Load dataset
    dataset_data = storage.load_dataset(dataset_path)

    character_ids = [character.id for character in dataset_data.characters]
    character_set = set(character_ids)
    if len(character_ids) != len(character_set):
        raise ValidationError("Dataset contains duplicate character ids")

    # Load roster
    roster_ids: list[str]
    if roster_path is None and default_roster_path is not None:
        if default_roster_path.exists():
            roster_ids = storage.load_roster(default_roster_path)
        else:
            roster_ids = sorted(character_set)
    elif roster_path is not None:
        roster_ids = storage.load_roster(roster_path)
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
        unit_sizes = storage.load_units(units_file_path)
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
            whitelist_pairs = storage.load_pairs(default_whitelist_path)
        else:
            whitelist_pairs = set()
    elif whitelist_path is not None:
        whitelist_pairs = storage.load_pairs(whitelist_path)
    else:
        whitelist_pairs = set()

    # Load blacklist
    blacklist_pairs: set[Pair]
    if blacklist_path is None and default_blacklist_path is not None:
        if default_blacklist_path.exists():
            blacklist_pairs = storage.load_pairs(default_blacklist_path)
        else:
            blacklist_pairs = set()
    elif blacklist_path is not None:
        blacklist_pairs = storage.load_pairs(blacklist_path)
    else:
        blacklist_pairs = set()

    # Validate whitelist
    invalid_whitelist = {
        pair for pair in whitelist_pairs if not pair.issubset(roster_set)
    }
    if invalid_whitelist:
        formatted = "; ".join(
            _format_pair(pair) for pair in _sort_pairs(invalid_whitelist)
        )
        raise ValidationError(
            f"Whitelist pair contains missing roster ids: {formatted}"
        )

    invalid_rapports = {pair for pair in whitelist_pairs if pair not in rapport_edges}
    if invalid_rapports:
        formatted = "; ".join(
            _format_pair(pair) for pair in _sort_pairs(invalid_rapports)
        )
        raise ValidationError(f"Whitelist pair is not a valid rapport: {formatted}")

    # Filter blacklist (warn, don't error)
    ignored_blacklist = {
        pair for pair in blacklist_pairs if not pair.issubset(roster_set)
    }
    if ignored_blacklist:
        formatted = "; ".join(
            _format_pair(pair) for pair in _sort_pairs(ignored_blacklist)
        )
        warnings.append(
            UserMessage(
                severity="warning",
                message=f"ignoring blacklist pairs not in roster: {formatted}",
            )
        )
    blacklist_pairs = {pair for pair in blacklist_pairs if pair.issubset(roster_set)}

    return (
        ProblemInputs(
            dataset=dataset_data,
            roster_ids=roster_ids,
            unit_sizes=unit_sizes,
            rapport_edges=rapport_edges,
            whitelist_pairs=whitelist_pairs,
            blacklist_pairs=blacklist_pairs,
        ),
        warnings,
    )


def load_combat_context(
    storage: StorageProtocol,
    dataset: Dataset,
    roster_set: set[str],
    combat_scoring_path: Path | None = None,
    character_classes_path: Path | None = None,
) -> tuple[CombatContext, list[UserMessage], list[CombatDiagnostic]]:
    """Load combat scoring context.

    Args:
        storage: Storage adapter for input loading.
        dataset: The loaded dataset.
        roster_set: Set of character IDs in the roster.
        combat_scoring_path: Path to combat scoring config, or None.
        character_classes_path: Path to class overrides CSV, or None.

    Returns:
        Tuple of CombatContext, warning messages, and combat diagnostics.

    Raises:
        ValidationError: If validation fails.
        InputError: If files cannot be read.
    """
    warnings: list[UserMessage] = []
    diagnostics: list[CombatDiagnostic] = []

    combat_scoring = CombatScoringConfig()
    if combat_scoring_path is not None and combat_scoring_path.exists():
        combat_scoring = storage.load_scoring(combat_scoring_path)

    overrides: dict[str, str] = {}
    if character_classes_path is not None and character_classes_path.exists():
        overrides = storage.load_character_classes(character_classes_path)

    character_set = {character.id for character in dataset.characters}
    unknown_override_characters = set(overrides) - character_set
    if unknown_override_characters:
        formatted = ", ".join(sorted(unknown_override_characters))
        raise ValidationError(
            f"Character class overrides contain unknown ids: {formatted}"
        )

    if dataset.classes and not dataset.character_classes:
        warnings.append(
            UserMessage(
                severity="warning",
                message=(
                    "dataset character classes are empty; combat scoring will "
                    "treat all members as unknown."
                ),
            )
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

    if dataset.classes and dataset.character_classes:
        missing_defaults = roster_set - set(effective_classes)
        if missing_defaults:
            diagnostics.append(missing_default_classes_diagnostic(missing_defaults))

    return (
        CombatContext(
            scoring=combat_scoring,
            effective_classes=effective_classes,
        ),
        warnings,
        diagnostics,
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


def _stats_summary(stats: BenchmarkStats) -> BenchmarkStatsSummary:
    return BenchmarkStatsSummary(
        count=stats.count,
        min=stats.minimum,
        max=stats.maximum,
        mean=stats.mean,
        p50=stats.median,
        p75=stats.p75,
        p90=stats.p90,
        std=stats.std,
    )


def run_solve(
    storage: StorageProtocol,
    dataset_path: Path,
    roster_path: Path | None,
    units_str: str | None,
    units_file_path: Path | None,
    whitelist_path: Path | None,
    blacklist_path: Path | None,
    combat_scoring_path: Path | None,
    character_classes_path: Path | None,
    *,
    seed: int,
    restarts: int,
    swap_iterations: int,
    min_combat_score: float | None,
    default_roster_path: Path | None = None,
    default_whitelist_path: Path | None = None,
    default_blacklist_path: Path | None = None,
) -> SolveRunResult:
    inputs, warnings = load_and_validate_problem(
        storage,
        dataset_path,
        roster_path,
        units_str,
        units_file_path,
        whitelist_path,
        blacklist_path,
        default_roster_path=default_roster_path,
        default_whitelist_path=default_whitelist_path,
        default_blacklist_path=default_blacklist_path,
    )

    combat_context, combat_warnings, combat_diagnostics = load_combat_context(
        storage,
        inputs.dataset,
        inputs.roster_set,
        combat_scoring_path=combat_scoring_path,
        character_classes_path=character_classes_path,
    )
    warnings.extend(combat_warnings)

    combat_score_fn = make_combat_score_fn(
        inputs.dataset,
        combat_context.effective_classes,
        combat_context.scoring,
    )

    if min_combat_score is not None and combat_score_fn is None:
        raise ValidationError(
            "Minimum combat score requires class data and character classes"
        )

    try:
        solution = solve(
            inputs.roster_ids,
            inputs.unit_sizes,
            inputs.rapport_edges,
            inputs.whitelist_pairs,
            inputs.blacklist_pairs,
            seed=seed,
            restarts=restarts,
            swap_iterations=swap_iterations,
            combat_score_fn=combat_score_fn,
            min_combat_score=min_combat_score,
        )
    except SolveError as exc:
        raise ValidationError(str(exc)) from exc

    if not inputs.dataset.classes or not combat_context.effective_classes:
        computed_combat = compute_combat_summary(
            [[] for _ in solution.units],
            {},
            [],
            CombatScoringConfig(),
        )
    else:
        computed_combat = compute_combat_summary(
            solution.units,
            combat_context.effective_classes,
            inputs.dataset.classes,
            combat_context.scoring,
        )
    solution = solution.model_copy(update={"combat": computed_combat})

    return SolveRunResult(
        solution=solution,
        unit_sizes=inputs.unit_sizes,
        combat_scoring=combat_context.scoring,
        warnings=warnings,
        combat_diagnostics=combat_diagnostics,
    )


def run_benchmark(
    storage: StorageProtocol,
    dataset_path: Path,
    roster_path: Path | None,
    units_str: str | None,
    units_file_path: Path | None,
    whitelist_path: Path | None,
    blacklist_path: Path | None,
    combat_scoring_path: Path | None,
    character_classes_path: Path | None,
    *,
    seed: int,
    trials: int,
    unit_samples: int,
    default_roster_path: Path | None = None,
    default_whitelist_path: Path | None = None,
    default_blacklist_path: Path | None = None,
) -> BenchmarkRunResult:
    inputs, warnings = load_and_validate_problem(
        storage,
        dataset_path,
        roster_path,
        units_str,
        units_file_path,
        whitelist_path,
        blacklist_path,
        default_roster_path=default_roster_path,
        default_whitelist_path=default_whitelist_path,
        default_blacklist_path=default_blacklist_path,
    )

    combat_context, combat_warnings, combat_diagnostics = load_combat_context(
        storage,
        inputs.dataset,
        inputs.roster_set,
        combat_scoring_path=combat_scoring_path,
        character_classes_path=character_classes_path,
    )
    warnings.extend(combat_warnings)

    combat_available = bool(inputs.dataset.classes and combat_context.effective_classes)
    rng = random.Random(seed)

    per_unit_size_stats: dict[str, BenchmarkStats] = {}
    per_unit_size_report: dict[str, UnitSizeReport] = {}
    for size in range(2, 7):
        values = []
        if combat_available:
            values = sample_unit_scores(
                inputs.roster_ids,
                size,
                unit_samples,
                rng,
                combat_context.effective_classes,
                inputs.dataset.classes,
                combat_context.scoring,
            )
        stats = compute_stats(values)
        size_key = str(size)
        per_unit_size_stats[size_key] = stats
        per_unit_size_report[size_key] = UnitSizeReport(
            stats=_stats_summary(stats),
            recommended_min=stats.p75,
            recommended_strict=stats.p90,
            samples=stats.count,
        )

    assignment_scores: list[float] = []
    failures = 0
    if combat_available:
        for _ in range(trials):
            try:
                assignment = generate_random_assignment(
                    inputs.roster_ids,
                    inputs.unit_sizes,
                    inputs.rapport_edges,
                    inputs.whitelist_pairs,
                    inputs.blacklist_pairs,
                    rng,
                )
            except SolveError as exc:
                raise ValidationError(str(exc)) from exc
            if assignment is None:
                failures += 1
                continue
            score = compute_combat_summary(
                assignment,
                combat_context.effective_classes,
                inputs.dataset.classes,
                combat_context.scoring,
            ).total_score
            assignment_scores.append(score)

    total_stats = compute_stats(assignment_scores)

    report = BenchmarkReport(
        combat_available=combat_available,
        inputs=BenchmarkInputSummary(
            seed=seed,
            units=inputs.unit_sizes,
            trials=trials,
            unit_samples=unit_samples,
        ),
        sample_counts=BenchmarkSampleCounts(
            total_trials=trials,
            total_successes=total_stats.count,
            total_failures=failures,
        ),
        total_score_stats=_stats_summary(total_stats),
        recommended_min_total=total_stats.p75,
        recommended_strict_total=total_stats.p90,
        per_unit_size=per_unit_size_report,
    )

    summary_lines = [
        "Combat benchmark",
        f"Combat data: {'available' if combat_available else 'missing'}",
        (
            "Total combat score (assignments): "
            f"n={total_stats.count}, failures={failures}, "
            f"mean={total_stats.mean:.2f}, p50={total_stats.median:.2f}, "
            f"p75={total_stats.p75:.2f}, p90={total_stats.p90:.2f}"
        ),
        (
            "Recommended minimum total: "
            f"{total_stats.p75:.2f} (strict {total_stats.p90:.2f})"
        ),
        "Per-unit size benchmarks (n, mean, p75, p90):",
    ]
    if not combat_available:
        summary_lines.append("Combat data missing; scores default to 0.")
    for size in range(2, 7):
        stats = per_unit_size_stats[str(size)]
        summary_lines.append(
            "Size "
            f"{size}: n={stats.count}, mean={stats.mean:.2f}, "
            f"p75={stats.p75:.2f}, p90={stats.p90:.2f}"
        )

    return BenchmarkRunResult(
        report=report,
        summary_lines=summary_lines,
        warnings=warnings,
        combat_diagnostics=combat_diagnostics,
    )


def normalize_rapport_entries(
    rapport_entries: list[object],
    character_ids: set[str],
) -> RapportSyncResult:
    id_order: list[str] = []
    rapport_map: dict[str, list[str]] = {}
    duplicate_entries = 0
    skipped_self = 0
    skipped_unknown = 0
    unknown_entry_ids: set[str] = set()

    for entry in rapport_entries:
        if not isinstance(entry, dict):
            continue
        entry_dict = cast("dict[str, object]", entry)
        raw_id = normalize_id(str(entry_dict.get("id", "")))
        if not raw_id:
            continue
        if raw_id not in character_ids:
            unknown_entry_ids.add(raw_id)
        raw_pairs = entry_dict.get("pairs") or []
        if not isinstance(raw_pairs, list):
            raise ValidationError(f"Rapport pairs for {raw_id} must be a list of ids")
        cleaned_pairs: list[str] = []
        seen: set[str] = set()
        for partner in raw_pairs:
            partner_id = normalize_id(str(partner))
            if not partner_id:
                continue
            if partner_id == raw_id:
                skipped_self += 1
                continue
            if partner_id in seen:
                continue
            seen.add(partner_id)
            cleaned_pairs.append(partner_id)
        if raw_id in rapport_map:
            duplicate_entries += 1
            existing = rapport_map[raw_id]
            existing_set = set(existing)
            for partner_id in cleaned_pairs:
                if partner_id not in existing_set:
                    existing.append(partner_id)
                    existing_set.add(partner_id)
        else:
            rapport_map[raw_id] = cleaned_pairs
            id_order.append(raw_id)

    adjacency = {character_id: set() for character_id in character_ids}
    for character_id, partners in rapport_map.items():
        if character_id not in character_ids:
            continue
        for partner_id in partners:
            if partner_id not in character_ids:
                skipped_unknown += 1
                continue
            if partner_id == character_id:
                skipped_self += 1
                continue
            adjacency[character_id].add(partner_id)
            adjacency[partner_id].add(character_id)

    normalized_entries: list[RapportListEntry] = []
    added_pairs = 0
    added_entries = 0

    for character_id in id_order:
        pairs = list(rapport_map.get(character_id, []))
        if character_id in character_ids:
            missing = sorted(adjacency[character_id] - set(pairs))
            if missing:
                pairs.extend(missing)
                added_pairs += len(missing)
        normalized_entries.append(RapportListEntry(id=character_id, pairs=pairs))

    missing_ids = sorted(
        character_id
        for character_id in character_ids
        if character_id not in rapport_map and adjacency[character_id]
    )
    for character_id in missing_ids:
        partners = sorted(adjacency[character_id])
        normalized_entries.append(RapportListEntry(id=character_id, pairs=partners))
        added_entries += 1
        added_pairs += len(partners)

    stats = RapportSyncStats(
        added_pairs=added_pairs,
        added_entries=added_entries,
        duplicate_entries=duplicate_entries,
        skipped_self=skipped_self,
        skipped_unknown=skipped_unknown,
        unknown_entry_ids=len(unknown_entry_ids),
    )
    normalized_payload = [entry.model_dump() for entry in normalized_entries]
    changed = normalized_payload != rapport_entries
    return RapportSyncResult(
        normalized=normalized_entries,
        stats=stats,
        changed=changed,
    )


def run_sync_rapports(raw_data: object, dataset: Dataset) -> RapportSyncResult:
    if not isinstance(raw_data, dict):
        raise ValidationError("Dataset JSON must be an object")

    raw_map = cast("dict[str, object]", raw_data)
    raw_rapports = raw_map.get("rapports") or []
    if not isinstance(raw_rapports, list):
        raise ValidationError("Dataset rapports must be a list")

    character_ids = {character.id for character in dataset.characters}
    rapport_entries = cast("list[object]", raw_rapports)
    return normalize_rapport_entries(rapport_entries, character_ids)
