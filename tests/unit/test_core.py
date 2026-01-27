"""Unit tests for core workflows."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from unicorn_armada.core import load_and_validate_problem, run_sync_rapports
from unicorn_armada.io import FileStorage
from unicorn_armada.models import Character, Dataset, RapportListEntry

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


def test_load_and_validate_problem_warns_on_blacklist(tmp_path: Path) -> None:
    """load_and_validate_problem should warn on blacklist pairs outside roster."""
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path)

    roster_path = tmp_path / "roster.csv"
    roster_path.write_text("id\nalice\nbob\n")

    blacklist_path = tmp_path / "blacklist.csv"
    blacklist_path.write_text("a,b\nalice,zoe\n")

    storage = FileStorage()
    inputs, warnings = load_and_validate_problem(
        storage,
        dataset_path,
        roster_path=None,
        units_str="2",
        units_file_path=None,
        whitelist_path=None,
        blacklist_path=blacklist_path,
        default_roster_path=roster_path,
    )

    assert inputs.unit_sizes == [2]
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    assert warnings[0].message.endswith("alice,zoe")


def test_run_sync_rapports_adds_missing_entries() -> None:
    """run_sync_rapports should add reciprocal entries when missing."""
    dataset = Dataset(
        characters=[Character(id="alice", name=None), Character(id="bob", name=None)],
        rapports=[RapportListEntry(id="alice", pairs=["bob"])],
    )
    raw_data = {
        "characters": [{"id": "alice"}, {"id": "bob"}],
        "rapports": [{"id": "alice", "pairs": ["bob"]}],
    }

    result = run_sync_rapports(raw_data, dataset)

    assert result.changed is True
    assert result.stats.added_entries == 1
    assert result.stats.added_pairs == 1
    normalized = [entry.model_dump() for entry in result.normalized]
    assert {entry["id"] for entry in normalized} == {"alice", "bob"}
