from __future__ import annotations

import json
import random
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, TypedDict

import typer

from .benchmark import (
    BenchmarkStats,
    compute_stats,
    generate_random_assignment,
    sample_unit_scores,
)
from .combat import (
    build_class_index,
    compute_combat_summary,
    format_diagnostic,
    missing_default_classes_diagnostic,
)
from .io import (
    InputError,
    load_character_classes_csv,
    load_combat_scoring_json,
    load_dataset,
    load_pairs_csv,
    load_roster_csv,
    load_units_json,
    parse_units_arg,
)
from .models import CombatScoringConfig
from .responses import APIResponse
from .solver import SolveError, solve
from .utils import Pair, normalize_id, pair_key

if TYPE_CHECKING:
    from collections.abc import Callable


class RapportEntry(TypedDict):
    """Raw rapport entry from dataset JSON."""

    id: str
    pairs: list[str]


# Type alias for benchmark unit size reports
UnitSizeReportData = dict[str, dict[str, float | int] | float | int]


app = typer.Typer(add_completion=False)

DEFAULT_DATASET = Path("data/dataset.json")
DEFAULT_ROSTER = Path("config/roster.csv")
DEFAULT_WHITELIST = Path("config/whitelist.csv")
DEFAULT_BLACKLIST = Path("config/blacklist.csv")
DEFAULT_CHARACTER_CLASSES = Path("config/character_classes.csv")
DEFAULT_COMBAT_SCORING = Path("config/combat_scoring.json")


@app.callback()
def root() -> None:
    """Rapport planner CLI."""


def format_pair(pair: Pair) -> str:
    left, right = sorted(pair)
    return f"{left},{right}"


def sort_pairs(pairs: set[Pair]) -> list[Pair]:
    return sorted(pairs, key=lambda pair: tuple(sorted(pair)))


def write_summary(
    path: Path,
    solution,
    units: list[int],
    combat_summary: bool = False,
    combat_scoring: CombatScoringConfig | None = None,
) -> None:
    lines = [f"Total rapports: {solution.total_rapports}"]
    if solution.combat is not None:
        lines.append(f"Total combat score: {solution.combat.total_score:.2f}")
    for idx, (unit, score) in enumerate(
        zip(solution.units, solution.unit_rapports, strict=False), start=1
    ):
        combat_score = None
        if solution.combat is not None and idx - 1 < len(solution.combat.unit_scores):
            combat_score = solution.combat.unit_scores[idx - 1]
        if combat_score is None:
            lines.append(f"Unit {idx} ({units[idx - 1]} slots): {score} rapports")
        else:
            lines.append(
                f"Unit {idx} ({units[idx - 1]} slots): {score} rapports, "
                f"{combat_score:.2f} combat"
            )
        lines.append(", ".join(unit) if unit else "(empty)")
    if solution.unassigned:
        lines.append("Unassigned:")
        lines.append(", ".join(solution.unassigned))
    path.write_text("\n".join(lines) + "\n")

    if combat_summary and solution.combat is not None and combat_scoring is not None:
        write_detailed_combat_summary(path, solution, units, combat_scoring)


def write_detailed_combat_summary(
    path: Path,
    solution,
    units: list[int],
    combat_scoring: CombatScoringConfig,
) -> None:
    lines = []
    lines.append("")
    lines.append("## Combat Summary Breakdown")
    lines.append("")

    for idx, unit_breakdown in enumerate(solution.combat.unit_breakdowns, start=1):
        unit_score = unit_breakdown.score
        lines.append(f"Unit {idx} ({unit_score:.2f} combat):")

        if unit_breakdown.roles:
            roles_str = ", ".join(sorted(unit_breakdown.roles.keys()))
            lines.append(f"  Roles: {roles_str}")
        else:
            lines.append("  Roles: (none)")

        if unit_breakdown.capabilities:
            caps_str = ", ".join(sorted(unit_breakdown.capabilities.keys()))
            lines.append(f"  Capabilities: {caps_str}")
        else:
            lines.append("  Capabilities: (none)")

        lines.append("")

    with path.open("a") as f:
        f.write("\n".join(lines))


def stats_to_dict(stats: BenchmarkStats) -> dict[str, float | int]:
    return {
        "count": stats.count,
        "min": stats.minimum,
        "max": stats.maximum,
        "mean": stats.mean,
        "p50": stats.median,
        "p75": stats.p75,
        "p90": stats.p90,
        "std": stats.std,
    }


def normalize_rapport_entries(
    rapport_entries: list[RapportEntry],
    character_ids: set[str],
) -> tuple[list[RapportEntry], dict[str, int]]:
    id_order: list[str] = []
    rapport_map: dict[str, list[str]] = {}
    duplicate_entries = 0
    skipped_self = 0
    skipped_unknown = 0
    unknown_entry_ids: set[str] = set()

    for entry in rapport_entries:
        if not isinstance(entry, dict):
            continue
        raw_id = normalize_id(str(entry.get("id", "")))
        if not raw_id:
            continue
        if raw_id not in character_ids:
            unknown_entry_ids.add(raw_id)
        raw_pairs = entry.get("pairs") or []
        if not isinstance(raw_pairs, list):
            raise typer.BadParameter(
                f"Rapport pairs for {raw_id} must be a list of ids"
            )
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

    normalized_entries: list[RapportEntry] = []
    added_pairs = 0
    added_entries = 0

    for character_id in id_order:
        pairs = list(rapport_map.get(character_id, []))
        if character_id in character_ids:
            missing = sorted(adjacency[character_id] - set(pairs))
            if missing:
                pairs.extend(missing)
                added_pairs += len(missing)
        normalized_entries.append({"id": character_id, "pairs": pairs})

    missing_ids = sorted(
        character_id
        for character_id in character_ids
        if character_id not in rapport_map and adjacency[character_id]
    )
    for character_id in missing_ids:
        partners = sorted(adjacency[character_id])
        normalized_entries.append({"id": character_id, "pairs": partners})
        added_entries += 1
        added_pairs += len(partners)

    stats = {
        "added_pairs": added_pairs,
        "added_entries": added_entries,
        "duplicate_entries": duplicate_entries,
        "skipped_self": skipped_self,
        "skipped_unknown": skipped_unknown,
        "unknown_entry_ids": len(unknown_entry_ids),
    }
    return normalized_entries, stats


def load_problem_inputs(
    dataset: Path | None,
    roster: Path | None,
    units: str | None,
    units_file: Path | None,
    whitelist: Path | None,
    blacklist: Path | None,
):
    dataset_path = dataset or DEFAULT_DATASET
    try:
        dataset_data = load_dataset(dataset_path)
    except InputError as exc:
        raise typer.BadParameter(str(exc)) from exc

    character_ids = [character.id for character in dataset_data.characters]
    character_set = set(character_ids)
    if len(character_ids) != len(character_set):
        raise typer.BadParameter("Dataset contains duplicate character ids")

    if roster is None:
        roster_path = DEFAULT_ROSTER
        if roster_path.exists():
            try:
                roster_ids = load_roster_csv(roster_path)
            except InputError as exc:
                raise typer.BadParameter(str(exc)) from exc
        else:
            roster_ids = sorted(character_set)
    else:
        try:
            roster_ids = load_roster_csv(roster)
        except InputError as exc:
            raise typer.BadParameter(str(exc)) from exc

    roster_set = set(roster_ids)
    if len(roster_ids) != len(roster_set):
        raise typer.BadParameter("Roster contains duplicate character ids")
    unknown = roster_set - character_set
    if unknown:
        raise typer.BadParameter(
            f"Roster contains unknown ids: {', '.join(sorted(unknown))}"
        )

    if units_file is not None and units is not None:
        raise typer.BadParameter("Provide either --units or --units-file, not both")
    if units_file is None and units is None:
        raise typer.BadParameter("Provide either --units or --units-file")

    try:
        if units_file is not None:
            unit_sizes = load_units_json(units_file)
        else:
            unit_sizes = parse_units_arg(units or "")
    except InputError as exc:
        raise typer.BadParameter(str(exc)) from exc

    rapport_edges: set[Pair] = set()
    for entry in dataset_data.rapports:
        if entry.id not in character_set:
            continue
        for partner in entry.pairs:
            if partner not in character_set:
                continue
            rapport_edges.add(pair_key(entry.id, partner))
    rapport_edges = {pair for pair in rapport_edges if pair.issubset(roster_set)}

    try:
        if whitelist is None:
            whitelist_pairs = (
                load_pairs_csv(DEFAULT_WHITELIST)
                if DEFAULT_WHITELIST.exists()
                else set()
            )
        else:
            whitelist_pairs = load_pairs_csv(whitelist)
        if blacklist is None:
            blacklist_pairs = (
                load_pairs_csv(DEFAULT_BLACKLIST)
                if DEFAULT_BLACKLIST.exists()
                else set()
            )
        else:
            blacklist_pairs = load_pairs_csv(blacklist)
    except InputError as exc:
        raise typer.BadParameter(str(exc)) from exc

    invalid_whitelist = {
        pair for pair in whitelist_pairs if not pair.issubset(roster_set)
    }
    if invalid_whitelist:
        formatted = "; ".join(
            format_pair(pair) for pair in sort_pairs(invalid_whitelist)
        )
        raise typer.BadParameter(
            f"Whitelist pair contains missing roster ids: {formatted}"
        )

    invalid_rapports = {pair for pair in whitelist_pairs if pair not in rapport_edges}
    if invalid_rapports:
        formatted = "; ".join(
            format_pair(pair) for pair in sort_pairs(invalid_rapports)
        )
        raise typer.BadParameter(f"Whitelist pair is not a valid rapport: {formatted}")

    ignored_blacklist = {
        pair for pair in blacklist_pairs if not pair.issubset(roster_set)
    }
    if ignored_blacklist:
        formatted = "; ".join(
            format_pair(pair) for pair in sort_pairs(ignored_blacklist)
        )
        typer.echo(f"Warning: ignoring blacklist pairs not in roster: {formatted}")
    blacklist_pairs = {pair for pair in blacklist_pairs if pair.issubset(roster_set)}

    return (
        dataset_data,
        roster_ids,
        unit_sizes,
        rapport_edges,
        whitelist_pairs,
        blacklist_pairs,
    )


def load_combat_context(dataset_data, roster_set: set[str]):
    combat_scoring = CombatScoringConfig()
    if DEFAULT_COMBAT_SCORING.exists():
        try:
            combat_scoring = load_combat_scoring_json(DEFAULT_COMBAT_SCORING)
        except InputError as exc:
            raise typer.BadParameter(str(exc)) from exc

    overrides: dict[str, str] = {}
    if DEFAULT_CHARACTER_CLASSES.exists():
        try:
            overrides = load_character_classes_csv(DEFAULT_CHARACTER_CLASSES)
        except InputError as exc:
            raise typer.BadParameter(str(exc)) from exc

    character_set = {character.id for character in dataset_data.characters}
    unknown_override_characters = set(overrides) - character_set
    if unknown_override_characters:
        formatted = ", ".join(sorted(unknown_override_characters))
        raise typer.BadParameter(
            f"Character class overrides contain unknown ids: {formatted}"
        )

    class_index = build_class_index(dataset_data.classes)
    class_lines = {line.id: line for line in dataset_data.class_lines}
    default_classes = {
        character_id: info.default_class
        for character_id, info in dataset_data.character_classes.items()
    }
    if dataset_data.classes and not dataset_data.character_classes:
        typer.echo(
            "Warning: dataset character classes are empty; combat scoring will treat "
            "all members as unknown."
        )

    override_class_ids = set(overrides.values())
    unknown_override_classes = {
        class_id for class_id in override_class_ids if class_id not in class_index
    }
    if unknown_override_classes:
        formatted = ", ".join(sorted(unknown_override_classes))
        raise typer.BadParameter(
            f"Character class overrides reference unknown classes: {formatted}"
        )

    for character_id, class_id in overrides.items():
        info = dataset_data.character_classes.get(character_id)
        if info is None:
            raise typer.BadParameter(
                f"Character {character_id} has no default class in dataset"
            )
        if info.class_line is None:
            if class_id != info.default_class:
                raise typer.BadParameter(
                    f"Character {character_id} override {class_id} is not allowed; "
                    "no class line is defined."
                )
            continue
        line = class_lines.get(info.class_line)
        if line is None:
            raise typer.BadParameter(
                f"Character {character_id} references unknown class line "
                f"{info.class_line}"
            )
        if class_id not in line.classes:
            raise typer.BadParameter(
                f"Character {character_id} override {class_id} is not part of class "
                f"line {info.class_line}"
            )

    effective_classes = dict(default_classes)
    effective_classes.update(overrides)

    if dataset_data.classes and dataset_data.character_classes:
        missing_defaults = roster_set - set(effective_classes)
        if missing_defaults:
            diagnostic = missing_default_classes_diagnostic(missing_defaults)
            typer.echo(format_diagnostic(diagnostic))

    return combat_scoring, effective_classes


@app.command()
def solve_units(
    dataset: Annotated[
        Path | None,
        typer.Option(help="Path to dataset JSON (default: data/dataset.json)"),
    ] = None,
    roster: Annotated[
        Path | None,
        typer.Option(
            help="CSV of available character ids (default: config/roster.csv)"
        ),
    ] = None,
    units: Annotated[
        str | None,
        typer.Option(help="Comma-separated list of unit sizes (e.g. 4,3,4,3)"),
    ] = None,
    units_file: Annotated[
        Path | None,
        typer.Option(help="JSON file containing unit sizes list"),
    ] = None,
    whitelist: Annotated[
        Path | None,
        typer.Option(help="CSV of required pairs (default: config/whitelist.csv)"),
    ] = None,
    blacklist: Annotated[
        Path | None,
        typer.Option(help="CSV of forbidden pairs (default: config/blacklist.csv)"),
    ] = None,
    seed: Annotated[int, typer.Option(help="Random seed for deterministic output")] = 0,
    restarts: Annotated[int, typer.Option(help="Greedy restart attempts")] = 50,
    swap_iterations: Annotated[
        int, typer.Option(help="Swap-improvement iterations")
    ] = 200,
    min_combat_score: Annotated[
        float | None,
        typer.Option(help="Minimum total combat score required for a solution"),
    ] = None,
    out: Annotated[Path, typer.Option(help="Output JSON path")] = Path(
        "out/solution.json"
    ),
    summary: Annotated[Path, typer.Option(help="Summary output path")] = Path(
        "out/summary.txt"
    ),
    combat_summary: Annotated[
        bool, typer.Option(help="Enable detailed combat breakdown in summary")
    ] = False,
) -> None:
    (
        dataset_data,
        roster_ids,
        unit_sizes,
        rapport_edges,
        whitelist_pairs,
        blacklist_pairs,
    ) = load_problem_inputs(dataset, roster, units, units_file, whitelist, blacklist)

    roster_set = set(roster_ids)
    combat_scoring, effective_classes = load_combat_context(dataset_data, roster_set)

    def _make_combat_score_fn() -> Callable[[list[list[str]]], float] | None:
        if not dataset_data.classes or not effective_classes:
            return None

        def score_fn(units: list[list[str]]) -> float:
            return compute_combat_summary(
                units,
                effective_classes,
                dataset_data.classes,
                combat_scoring,
            ).total_score

        return score_fn

    combat_score_fn = _make_combat_score_fn()

    if min_combat_score is not None and combat_score_fn is None:
        raise typer.BadParameter(
            "Minimum combat score requires class data and character classes"
        )

    try:
        solution = solve(
            roster_ids,
            unit_sizes,
            rapport_edges,
            whitelist_pairs,
            blacklist_pairs,
            seed=seed,
            restarts=restarts,
            swap_iterations=swap_iterations,
            combat_score_fn=combat_score_fn,
            min_combat_score=min_combat_score,
        )
    except SolveError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if not dataset_data.classes or not effective_classes:
        computed_combat = compute_combat_summary(
            [[] for _ in solution.units],
            {},
            [],
            CombatScoringConfig(),
        )
    else:
        computed_combat = compute_combat_summary(
            solution.units,
            effective_classes,
            dataset_data.classes,
            combat_scoring,
        )
    solution = solution.model_copy(update={"combat": computed_combat})

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(solution.model_dump_json(indent=2))

    summary.parent.mkdir(parents=True, exist_ok=True)
    write_summary(summary, solution, unit_sizes, combat_summary, combat_scoring)

    typer.echo(f"Total rapports: {solution.total_rapports}")
    typer.echo(f"Wrote solution to {out}")
    typer.echo(f"Wrote summary to {summary}")


@app.command()
def benchmark_units(
    dataset: Annotated[
        Path | None,
        typer.Option(help="Path to dataset JSON (default: data/dataset.json)"),
    ] = None,
    roster: Annotated[
        Path | None,
        typer.Option(
            help="CSV of available character ids (default: config/roster.csv)"
        ),
    ] = None,
    units: Annotated[
        str | None,
        typer.Option(help="Comma-separated list of unit sizes (e.g. 4,3,4,3)"),
    ] = None,
    units_file: Annotated[
        Path | None,
        typer.Option(help="JSON file containing unit sizes list"),
    ] = None,
    whitelist: Annotated[
        Path | None,
        typer.Option(help="CSV of required pairs (default: config/whitelist.csv)"),
    ] = None,
    blacklist: Annotated[
        Path | None,
        typer.Option(help="CSV of forbidden pairs (default: config/blacklist.csv)"),
    ] = None,
    seed: Annotated[int, typer.Option(help="Random seed for deterministic output")] = 0,
    trials: Annotated[
        int, typer.Option(help="Full-assignment samples to generate")
    ] = 200,
    unit_samples: Annotated[
        int, typer.Option(help="Random unit samples per size (2-6 slots)")
    ] = 2000,
    out: Annotated[Path, typer.Option(help="Output JSON path")] = Path(
        "out/benchmark.json"
    ),
    summary: Annotated[Path, typer.Option(help="Summary output path")] = Path(
        "out/benchmark.txt"
    ),
) -> None:
    (
        dataset_data,
        roster_ids,
        unit_sizes,
        rapport_edges,
        whitelist_pairs,
        blacklist_pairs,
    ) = load_problem_inputs(dataset, roster, units, units_file, whitelist, blacklist)

    roster_set = set(roster_ids)
    combat_scoring, effective_classes = load_combat_context(dataset_data, roster_set)

    combat_available = bool(dataset_data.classes and effective_classes)
    rng = random.Random(seed)

    per_unit_size_stats: dict[str, BenchmarkStats] = {}
    per_unit_size_report: dict[str, UnitSizeReportData] = {}
    for size in range(2, 7):
        values = []
        if combat_available:
            values = sample_unit_scores(
                roster_ids,
                size,
                unit_samples,
                rng,
                effective_classes,
                dataset_data.classes,
                combat_scoring,
            )
        stats = compute_stats(values)
        size_key = str(size)
        per_unit_size_stats[size_key] = stats
        per_unit_size_report[size_key] = {
            "stats": stats_to_dict(stats),
            "recommended_min": stats.p75,
            "recommended_strict": stats.p90,
            "samples": stats.count,
        }

    assignment_scores: list[float] = []
    failures = 0
    if combat_available:
        for _ in range(trials):
            try:
                assignment = generate_random_assignment(
                    roster_ids,
                    unit_sizes,
                    rapport_edges,
                    whitelist_pairs,
                    blacklist_pairs,
                    rng,
                )
            except SolveError as exc:
                raise typer.BadParameter(str(exc)) from exc
            if assignment is None:
                failures += 1
                continue
            score = compute_combat_summary(
                assignment,
                effective_classes,
                dataset_data.classes,
                combat_scoring,
            ).total_score
            assignment_scores.append(score)

    total_stats = compute_stats(assignment_scores)

    report = {
        "combat_available": combat_available,
        "inputs": {
            "seed": seed,
            "units": unit_sizes,
            "trials": trials,
            "unit_samples": unit_samples,
        },
        "sample_counts": {
            "total_trials": trials,
            "total_successes": total_stats.count,
            "total_failures": failures,
        },
        "total_score_stats": stats_to_dict(total_stats),
        "recommended_min_total": total_stats.p75,
        "recommended_strict_total": total_stats.p90,
        "per_unit_size": per_unit_size_report,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    response = APIResponse.success(report)
    out.write_text(response.model_dump_json(indent=2) + "\n")

    summary.parent.mkdir(parents=True, exist_ok=True)
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
    summary.write_text("\n".join(summary_lines) + "\n")

    typer.echo(f"Wrote benchmark to {out}")
    typer.echo(f"Wrote benchmark summary to {summary}")


@app.command()
def sync_rapports(
    dataset: Annotated[
        Path | None,
        typer.Option(help="Path to dataset JSON (default: data/dataset.json)"),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option(help="Output dataset JSON path (default: overwrite dataset file)"),
    ] = None,
) -> None:
    dataset_path = dataset or DEFAULT_DATASET
    try:
        raw_data = json.loads(dataset_path.read_text())
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"Dataset not found: {dataset_path}") from exc
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Dataset JSON is invalid: {dataset_path}") from exc

    if not isinstance(raw_data, dict):
        raise typer.BadParameter("Dataset JSON must be an object")

    try:
        dataset_data = load_dataset(dataset_path)
    except InputError as exc:
        raise typer.BadParameter(str(exc)) from exc

    raw_rapports = raw_data.get("rapports") or []
    if not isinstance(raw_rapports, list):
        raise typer.BadParameter("Dataset rapports must be a list")

    character_ids = {character.id for character in dataset_data.characters}
    normalized, stats = normalize_rapport_entries(raw_rapports, character_ids)

    out_path = out or dataset_path
    if normalized == raw_rapports and out_path == dataset_path:
        typer.echo("Rapports already bidirectional; no changes needed.")
        return

    raw_data["rapports"] = normalized
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(raw_data, indent=2) + "\n")

    typer.echo(f"Wrote cleaned dataset to {out_path}")
    typer.echo(f"Added {stats['added_pairs']} reciprocal pairs.")
    if stats["added_entries"]:
        typer.echo(f"Added {stats['added_entries']} new rapport entries.")
    if stats["duplicate_entries"]:
        typer.echo(f"Collapsed {stats['duplicate_entries']} duplicate entries.")
    if stats["skipped_self"]:
        typer.echo(f"Removed {stats['skipped_self']} self-pairs.")
    if stats["skipped_unknown"]:
        typer.echo(
            f"Ignored {stats['skipped_unknown']} pairs with unknown character ids."
        )
    if stats["unknown_entry_ids"]:
        typer.echo(
            f"Warning: {stats['unknown_entry_ids']} rapport entries "
            "use unknown character ids."
        )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
