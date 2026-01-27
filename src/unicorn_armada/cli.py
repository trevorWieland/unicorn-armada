from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from uuid import uuid4

import typer

from .combat import format_diagnostic
from .core import ValidationError, run_benchmark, run_solve, run_sync_rapports
from .io import FileStorage, InputError
from .logging import Events, Logger
from .models import RapportSyncReport
from .responses import APIResponse

if TYPE_CHECKING:
    from .models import CombatScoringConfig

app = typer.Typer(add_completion=False)

DEFAULT_DATASET = Path("data/dataset.json")
DEFAULT_ROSTER = Path("config/roster.csv")
DEFAULT_WHITELIST = Path("config/whitelist.csv")
DEFAULT_BLACKLIST = Path("config/blacklist.csv")
DEFAULT_CHARACTER_CLASSES = Path("config/character_classes.csv")
DEFAULT_COMBAT_SCORING = Path("config/combat_scoring.json")
DEFAULT_SYNC_REPORT = Path("out/sync-rapports.json")


@app.callback()
def root() -> None:
    """Rapport planner CLI."""


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
    logger = Logger(run_id=uuid4().hex)
    storage = FileStorage()
    dataset_path = dataset or DEFAULT_DATASET
    logger.info(
        Events.RUN_STARTED,
        "solve-units started",
        data={
            "command": "solve-units",
            "dataset": str(dataset_path),
            "roster": str(roster) if roster else None,
            "units": units,
            "units_file": str(units_file) if units_file else None,
            "whitelist": str(whitelist) if whitelist else None,
            "blacklist": str(blacklist) if blacklist else None,
            "seed": seed,
            "restarts": restarts,
            "swap_iterations": swap_iterations,
            "min_combat_score": min_combat_score,
            "out": str(out),
            "summary": str(summary),
            "combat_summary": combat_summary,
        },
    )
    try:
        result = run_solve(
            storage=storage,
            dataset_path=dataset_path,
            roster_path=roster,
            units_str=units,
            units_file_path=units_file,
            whitelist_path=whitelist,
            blacklist_path=blacklist,
            combat_scoring_path=DEFAULT_COMBAT_SCORING,
            character_classes_path=DEFAULT_CHARACTER_CLASSES,
            seed=seed,
            restarts=restarts,
            swap_iterations=swap_iterations,
            min_combat_score=min_combat_score,
            default_roster_path=DEFAULT_ROSTER,
            default_whitelist_path=DEFAULT_WHITELIST,
            default_blacklist_path=DEFAULT_BLACKLIST,
        )
    except (ValidationError, InputError) as exc:
        logger.error(Events.RUN_FAILED, "solve-units failed", data={"error": str(exc)})
        raise typer.BadParameter(str(exc)) from exc

    for warning in result.warnings:
        if warning.severity == "warning":
            typer.echo(f"Warning: {warning.message}")
            logger.warn(
                "warning_emitted",
                warning.message,
                data={"severity": warning.severity},
            )
        else:
            typer.echo(warning.message)
            logger.info(
                "info_emitted",
                warning.message,
                data={"severity": warning.severity},
            )
    for diagnostic in result.combat_diagnostics:
        typer.echo(format_diagnostic(diagnostic))
        if diagnostic.severity == "error":
            logger.error(
                "diagnostic_emitted",
                diagnostic.message,
                data={"code": diagnostic.code, "subject": diagnostic.subject},
            )
        else:
            logger.warn(
                "diagnostic_emitted",
                diagnostic.message,
                data={"code": diagnostic.code, "subject": diagnostic.subject},
            )

    solution = result.solution

    out.parent.mkdir(parents=True, exist_ok=True)
    response = APIResponse.success(solution)
    out.write_text(response.model_dump_json(indent=2) + "\n")
    logger.info(
        Events.DATA_WRITTEN,
        "solution output written",
        data={"path": str(out)},
    )

    summary.parent.mkdir(parents=True, exist_ok=True)
    write_summary(
        summary,
        solution,
        result.unit_sizes,
        combat_summary,
        result.combat_scoring,
    )
    logger.info(
        Events.DATA_WRITTEN,
        "summary output written",
        data={"path": str(summary)},
    )

    typer.echo(f"Total rapports: {solution.total_rapports}")
    typer.echo(f"Wrote solution to {out}")
    typer.echo(f"Wrote summary to {summary}")
    logger.info(
        Events.RUN_COMPLETED,
        "solve-units completed",
        data={
            "total_rapports": solution.total_rapports,
            "combat_total": solution.combat.total_score if solution.combat else None,
        },
    )


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
    logger = Logger(run_id=uuid4().hex)
    storage = FileStorage()
    dataset_path = dataset or DEFAULT_DATASET
    logger.info(
        Events.RUN_STARTED,
        "benchmark-units started",
        data={
            "command": "benchmark-units",
            "dataset": str(dataset_path),
            "roster": str(roster) if roster else None,
            "units": units,
            "units_file": str(units_file) if units_file else None,
            "whitelist": str(whitelist) if whitelist else None,
            "blacklist": str(blacklist) if blacklist else None,
            "seed": seed,
            "trials": trials,
            "unit_samples": unit_samples,
            "out": str(out),
            "summary": str(summary),
        },
    )
    try:
        result = run_benchmark(
            storage=storage,
            dataset_path=dataset_path,
            roster_path=roster,
            units_str=units,
            units_file_path=units_file,
            whitelist_path=whitelist,
            blacklist_path=blacklist,
            combat_scoring_path=DEFAULT_COMBAT_SCORING,
            character_classes_path=DEFAULT_CHARACTER_CLASSES,
            seed=seed,
            trials=trials,
            unit_samples=unit_samples,
            default_roster_path=DEFAULT_ROSTER,
            default_whitelist_path=DEFAULT_WHITELIST,
            default_blacklist_path=DEFAULT_BLACKLIST,
        )
    except (ValidationError, InputError) as exc:
        logger.error(
            Events.RUN_FAILED, "benchmark-units failed", data={"error": str(exc)}
        )
        raise typer.BadParameter(str(exc)) from exc

    for warning in result.warnings:
        if warning.severity == "warning":
            typer.echo(f"Warning: {warning.message}")
            logger.warn(
                "warning_emitted",
                warning.message,
                data={"severity": warning.severity},
            )
        else:
            typer.echo(warning.message)
            logger.info(
                "info_emitted",
                warning.message,
                data={"severity": warning.severity},
            )
    for diagnostic in result.combat_diagnostics:
        typer.echo(format_diagnostic(diagnostic))
        if diagnostic.severity == "error":
            logger.error(
                "diagnostic_emitted",
                diagnostic.message,
                data={"code": diagnostic.code, "subject": diagnostic.subject},
            )
        else:
            logger.warn(
                "diagnostic_emitted",
                diagnostic.message,
                data={"code": diagnostic.code, "subject": diagnostic.subject},
            )

    out.parent.mkdir(parents=True, exist_ok=True)
    response = APIResponse.success(result.report)
    out.write_text(response.model_dump_json(indent=2) + "\n")
    logger.info(
        Events.DATA_WRITTEN,
        "benchmark output written",
        data={"path": str(out)},
    )

    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text("\n".join(result.summary_lines) + "\n")
    logger.info(
        Events.DATA_WRITTEN,
        "benchmark summary written",
        data={"path": str(summary)},
    )

    typer.echo(f"Wrote benchmark to {out}")
    typer.echo(f"Wrote benchmark summary to {summary}")
    logger.info(
        Events.RUN_COMPLETED,
        "benchmark-units completed",
        data={"total_trials": result.report.sample_counts.total_trials},
    )


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
    report: Annotated[
        Path,
        typer.Option(help="Output JSON report path"),
    ] = DEFAULT_SYNC_REPORT,
) -> None:
    logger = Logger(run_id=uuid4().hex)
    dataset_path = dataset or DEFAULT_DATASET
    logger.info(
        Events.RUN_STARTED,
        "sync-rapports started",
        data={
            "command": "sync-rapports",
            "dataset": str(dataset_path),
            "out": str(out) if out else None,
            "report": str(report),
        },
    )
    try:
        raw_data = json.loads(dataset_path.read_text())
    except FileNotFoundError as exc:
        logger.error(
            Events.RUN_FAILED, "sync-rapports failed", data={"error": str(exc)}
        )
        raise typer.BadParameter(f"Dataset not found: {dataset_path}") from exc
    except json.JSONDecodeError as exc:
        logger.error(
            Events.RUN_FAILED, "sync-rapports failed", data={"error": str(exc)}
        )
        raise typer.BadParameter(f"Dataset JSON is invalid: {dataset_path}") from exc
    logger.info(
        Events.DATA_LOADED,
        "raw dataset loaded",
        data={"path": str(dataset_path)},
    )

    storage = FileStorage()
    try:
        dataset_data = storage.load_dataset(dataset_path)
    except InputError as exc:
        logger.error(
            Events.RUN_FAILED, "sync-rapports failed", data={"error": str(exc)}
        )
        raise typer.BadParameter(str(exc)) from exc

    try:
        result = run_sync_rapports(raw_data, dataset_data)
    except ValidationError as exc:
        logger.error(
            Events.RUN_FAILED, "sync-rapports failed", data={"error": str(exc)}
        )
        raise typer.BadParameter(str(exc)) from exc

    out_path = out or dataset_path
    wrote_dataset = False
    if not result.changed and out_path == dataset_path:
        typer.echo("Rapports already bidirectional; no changes needed.")
    else:
        raw_data["rapports"] = [entry.model_dump() for entry in result.normalized]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(raw_data, indent=2) + "\n")
        wrote_dataset = True
        logger.info(
            Events.DATA_WRITTEN,
            "dataset written",
            data={"path": str(out_path)},
        )

        stats = result.stats
        typer.echo(f"Wrote cleaned dataset to {out_path}")
        typer.echo(f"Added {stats.added_pairs} reciprocal pairs.")
        if stats.added_entries:
            typer.echo(f"Added {stats.added_entries} new rapport entries.")
        if stats.duplicate_entries:
            typer.echo(f"Collapsed {stats.duplicate_entries} duplicate entries.")
        if stats.skipped_self:
            typer.echo(f"Removed {stats.skipped_self} self-pairs.")
        if stats.skipped_unknown:
            typer.echo(
                f"Ignored {stats.skipped_unknown} pairs with unknown character ids."
            )
        if stats.unknown_entry_ids:
            typer.echo(
                f"Warning: {stats.unknown_entry_ids} rapport entries "
                "use unknown character ids."
            )

    report.parent.mkdir(parents=True, exist_ok=True)
    report_payload = RapportSyncReport(
        changed=result.changed,
        output_path=str(out_path),
        stats=result.stats,
    )
    report_response = APIResponse.success(report_payload)
    report.write_text(report_response.model_dump_json(indent=2) + "\n")
    logger.info(
        Events.DATA_WRITTEN,
        "sync report written",
        data={"path": str(report)},
    )
    typer.echo(f"Wrote sync report to {report}")
    logger.info(
        Events.RUN_COMPLETED,
        "sync-rapports completed",
        data={"changed": result.changed, "wrote_dataset": wrote_dataset},
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
