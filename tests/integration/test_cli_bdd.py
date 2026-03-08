"""Integration tests for CLI commands."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from unicorn_armada.cli import app

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


def _write_dataset(path: Path) -> None:
    data = {
        "characters": [{"id": "alice"}, {"id": "bob"}],
        "rapports": [
            {"id": "alice", "pairs": ["bob"]},
            {"id": "bob", "pairs": ["alice"]},
        ],
    }
    path.write_text(json.dumps(data))


def test_cli_solve_units_writes_outputs(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    # Given a minimal dataset and roster
    dataset_path = tmp_path / "dataset.json"
    roster_path = tmp_path / "roster.csv"
    _write_dataset(dataset_path)
    roster_path.write_text("id\nalice\nbob\n")
    out_path = tmp_path / "out" / "solution.json"
    summary_path = tmp_path / "out" / "summary.txt"
    monkeypatch.chdir(tmp_path)

    # When invoking the CLI solve command
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "solve-units",
            "--dataset",
            str(dataset_path),
            "--roster",
            str(roster_path),
            "--units",
            "2",
            "--seed",
            "0",
            "--restarts",
            "1",
            "--swap-iterations",
            "1",
            "--out",
            str(out_path),
            "--summary",
            str(summary_path),
        ],
    )

    # Then outputs are written with expected text
    assert result.exit_code == 0
    assert out_path.exists() is True
    assert summary_path.exists() is True
    assert "Total rapports:" in result.output
    assert f"Wrote solution to {out_path}" in result.output


def test_cli_sync_rapports_updates_dataset(
    tmp_path: Path,
) -> None:
    # Given a dataset with a missing reciprocal pair
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        '{"characters":[{"id":"alice"},{"id":"bob"}],'
        '"rapports":[{"id":"alice","pairs":["bob"]}]}'
    )
    out_path = tmp_path / "updated.json"
    report_path = tmp_path / "report.json"

    # When invoking the CLI sync command
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "sync-rapports",
            "--dataset",
            str(dataset_path),
            "--out",
            str(out_path),
            "--report",
            str(report_path),
        ],
    )

    # Then the dataset and report are updated
    assert result.exit_code == 0
    assert out_path.exists() is True
    assert report_path.exists() is True
    updated = json.loads(out_path.read_text())
    rapport_ids = {entry["id"] for entry in updated["rapports"]}
    assert "bob" in rapport_ids
