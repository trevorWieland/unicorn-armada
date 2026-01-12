from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .io import (
    InputError,
    load_dataset,
    load_pairs_csv,
    load_roster_csv,
    load_units_json,
    parse_units_arg,
)
from .solver import SolveError, solve
from .utils import Pair, pair_key


app = typer.Typer(add_completion=False)

DEFAULT_DATASET = Path("data/dataset.json")
DEFAULT_ROSTER = Path("config/roster.csv")
DEFAULT_WHITELIST = Path("config/whitelist.csv")
DEFAULT_BLACKLIST = Path("config/blacklist.csv")


@app.callback()
def root() -> None:
    """Bond planner CLI."""


def format_pair(pair: Pair) -> str:
    left, right = sorted(pair)
    return f"{left},{right}"


def sort_pairs(pairs: set[Pair]) -> list[Pair]:
    return sorted(pairs, key=lambda pair: tuple(sorted(pair)))


def write_summary(path: Path, solution, units: list[int]) -> None:
    lines = [f"Total bonds: {solution.total_bonds}"]
    for idx, (unit, score) in enumerate(
        zip(solution.units, solution.unit_bonds), start=1
    ):
        lines.append(f"Unit {idx} ({units[idx - 1]} slots): {score} bonds")
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
        None, "--roster", help="CSV of available character ids (default: config/roster.csv)"
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
        None, "--whitelist", help="CSV of required pairs (default: config/whitelist.csv)"
    ),
    blacklist: Optional[Path] = typer.Option(
        None, "--blacklist", help="CSV of forbidden pairs (default: config/blacklist.csv)"
    ),
    seed: int = typer.Option(0, help="Random seed for deterministic output"),
    restarts: int = typer.Option(50, help="Greedy restart attempts"),
    swap_iterations: int = typer.Option(200, help="Swap-improvement iterations"),
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

    bond_edges: set[Pair] = set()
    for entry in dataset_data.bonds:
        if entry.id not in character_set:
            continue
        for partner in entry.pairs:
            if partner not in character_set:
                continue
            bond_edges.add(pair_key(entry.id, partner))
    bond_edges = {pair for pair in bond_edges if pair.issubset(roster_set)}

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

    invalid_bonds = {pair for pair in whitelist_pairs if pair not in bond_edges}
    if invalid_bonds:
        formatted = "; ".join(format_pair(pair) for pair in sort_pairs(invalid_bonds))
        raise typer.BadParameter(f"Whitelist pair is not a valid bond: {formatted}")

    ignored_blacklist = {
        pair for pair in blacklist_pairs if not pair.issubset(roster_set)
    }
    if ignored_blacklist:
        formatted = "; ".join(
            format_pair(pair) for pair in sort_pairs(ignored_blacklist)
        )
        typer.echo(f"Warning: ignoring blacklist pairs not in roster: {formatted}")
    blacklist_pairs = {pair for pair in blacklist_pairs if pair.issubset(roster_set)}

    try:
        solution = solve(
            roster_ids,
            unit_sizes,
            bond_edges,
            whitelist_pairs,
            blacklist_pairs,
            seed=seed,
            restarts=restarts,
            swap_iterations=swap_iterations,
        )
    except SolveError as exc:
        raise typer.BadParameter(str(exc)) from exc

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(solution.model_dump_json(indent=2))

    summary.parent.mkdir(parents=True, exist_ok=True)
    write_summary(summary, solution, unit_sizes)

    typer.echo(f"Total bonds: {solution.total_bonds}")
    typer.echo(f"Wrote solution to {out}")
    typer.echo(f"Wrote summary to {summary}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
