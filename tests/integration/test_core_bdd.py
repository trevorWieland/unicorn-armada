"""Integration tests for core workflows."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from unicorn_armada.core import run_solve
from unicorn_armada.io import FileStorage

if TYPE_CHECKING:
    from pathlib import Path


def _write_dataset(path: Path) -> None:
    data = {
        "characters": [{"id": "alice"}, {"id": "bob"}],
        "rapports": [
            {"id": "alice", "pairs": ["bob"]},
            {"id": "bob", "pairs": ["alice"]},
        ],
    }
    path.write_text(json.dumps(data))


def test_run_solve_minimal_dataset(tmp_path: Path) -> None:
    # Given a minimal dataset and roster
    dataset_path = tmp_path / "dataset.json"
    roster_path = tmp_path / "roster.csv"
    _write_dataset(dataset_path)
    roster_path.write_text("id\nalice\nbob\n")
    storage = FileStorage()

    # When running the solve workflow
    result = run_solve(
        storage=storage,
        dataset_path=dataset_path,
        roster_path=roster_path,
        units_str="2",
        units_file_path=None,
        whitelist_path=None,
        blacklist_path=None,
        combat_scoring_path=None,
        character_classes_path=None,
        seed=0,
        restarts=1,
        swap_iterations=1,
        min_combat_score=None,
    )

    # Then solution and combat summary are produced
    assert result.unit_sizes == [2]
    assert result.solution.combat is not None
    assert result.solution.combat.total_score == 0.0
    assert result.warnings == []
    assert result.combat_diagnostics == []
