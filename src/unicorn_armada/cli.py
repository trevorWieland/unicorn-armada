from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .combat import build_class_index, compute_combat_summary
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
from .solver import SolveError, solve
from .utils import Pair, pair_key


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


def write_summary(path: Path, solution, units: list[int]) -> None:
    lines = [f"Total rapports: {solution.total_rapports}"]
    if solution.combat is not None:
        lines.append(f"Total combat score: {solution.combat.total_score:.2f}")
    for idx, (unit, score) in enumerate(
        zip(solution.units, solution.unit_rapports), start=1
    ):
        combat_score = None
        if solution.combat is not None:
            if idx - 1 < len(solution.combat.unit_scores):
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


@app.command()
def solve_units(
    dataset: Optional[Path] = typer.Option(
        None, "--dataset", help="Path to dataset JSON (default: data/dataset.json)"
    ),
    roster: Optional[Path] = typer.Option(
        None,
        "--roster",
        help="CSV of available character ids (default: config/roster.csv)",
    ),
    units: Optional[str] = typer.Option(
        None,
        "--units",
        help="Comma-separated list of unit sizes (e.g. 4,3,4,3)",
    ),
    units_file: Optional[Path] = typer.Option(
        None, "--units-file", help="JSON file containing unit sizes list"
    ),
    whitelist: Optional[Path] = typer.Option(
        None,
        "--whitelist",
        help="CSV of required pairs (default: config/whitelist.csv)",
    ),
    blacklist: Optional[Path] = typer.Option(
        None,
        "--blacklist",
        help="CSV of forbidden pairs (default: config/blacklist.csv)",
    ),
    seed: int = typer.Option(0, help="Random seed for deterministic output"),
    restarts: int = typer.Option(50, help="Greedy restart attempts"),
    swap_iterations: int = typer.Option(200, help="Swap-improvement iterations"),
    min_combat_score: Optional[float] = typer.Option(
        None,
        "--min-combat-score",
        help="Minimum total combat score required for a solution",
    ),
    out: Path = typer.Option(
        Path("out/solution.json"), "--out", help="Output JSON path"
    ),
    summary: Path = typer.Option(
        Path("out/summary.txt"), "--summary", help="Summary output path"
    ),
) -> None:
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
            formatted = ", ".join(sorted(missing_defaults))
            typer.echo(
                f"Warning: missing default classes for roster characters: {formatted}"
            )

    combat_score_fn = None
    if dataset_data.classes and effective_classes:

        def combat_score_fn(units: list[list[str]]) -> float:
            return compute_combat_summary(
                units,
                effective_classes,
                dataset_data.classes,
                combat_scoring,
            ).total_score

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
        combat_summary = compute_combat_summary(
            [[] for _ in solution.units],
            {},
            [],
            CombatScoringConfig(),
        )
    else:
        combat_summary = compute_combat_summary(
            solution.units,
            effective_classes,
            dataset_data.classes,
            combat_scoring,
        )
    solution = solution.model_copy(update={"combat": combat_summary})

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(solution.model_dump_json(indent=2))

    summary.parent.mkdir(parents=True, exist_ok=True)
    write_summary(summary, solution, unit_sizes)

    typer.echo(f"Total rapports: {solution.total_rapports}")
    typer.echo(f"Wrote solution to {out}")
    typer.echo(f"Wrote summary to {summary}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
