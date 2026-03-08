"""Unit tests for core workflows."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from unicorn_armada.core import (
    ValidationError,
    apply_preset,
    load_and_validate_problem,
    load_combat_context,
    make_combat_score_fn,
    run_benchmark,
    run_solve,
    run_sync_rapports,
)
from unicorn_armada.io import FileStorage
from unicorn_armada.models import (
    Character,
    CharacterClassInfo,
    ClassDefinition,
    CombatScoringConfig,
    Dataset,
    RapportListEntry,
    Solution,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write_dataset(
    path: Path,
    *,
    characters: tuple[str, ...] | None = None,
    rapports: list[dict[str, object]] | None = None,
    classes: list[dict[str, object]] | None = None,
    class_lines: list[dict[str, object]] | None = None,
    character_classes: dict[str, object] | None = None,
) -> None:
    if characters is None:
        characters = ("alice", "bob")
    if rapports is None:
        rapports = [
            {"id": "alice", "pairs": ["bob"]},
            {"id": "bob", "pairs": ["alice"]},
        ]
    data: dict[str, object] = {
        "characters": [{"id": entry} for entry in characters],
        "rapports": rapports,
    }
    if classes is not None:
        data["classes"] = classes
    if class_lines is not None:
        data["class_lines"] = class_lines
    if character_classes is not None:
        data["character_classes"] = character_classes
    path.write_text(json.dumps(data))


def _class_definition(class_id: str = "warrior") -> dict[str, object]:
    return {
        "id": class_id,
        "name": class_id.title(),
        "roles": ["frontline"],
        "capabilities": [],
        "row_preference": "front",
        "class_types": ["infantry"],
        "unit_type": "infantry",
        "assist_type": "none",
        "leader_effect": None,
        "class_trait": None,
        "stamina": 1,
        "mobility": 1,
        "promotes_to": None,
    }


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


def test_load_and_validate_problem_rejects_duplicate_character_ids(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(
        dataset_path,
        characters=("alice", "alice"),
        rapports=[{"id": "alice", "pairs": []}],
    )

    storage = FileStorage()
    with pytest.raises(ValidationError, match="duplicate character ids"):
        load_and_validate_problem(
            storage,
            dataset_path,
            roster_path=None,
            units_str="2",
            units_file_path=None,
            whitelist_path=None,
            blacklist_path=None,
        )


def test_load_and_validate_problem_rejects_unknown_roster_ids(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path, characters=("alice",))
    roster_path = tmp_path / "roster.csv"
    roster_path.write_text("id\nalice\nzoe\n")

    storage = FileStorage()
    with pytest.raises(ValidationError, match="Roster contains unknown ids"):
        load_and_validate_problem(
            storage,
            dataset_path,
            roster_path=roster_path,
            units_str="1",
            units_file_path=None,
            whitelist_path=None,
            blacklist_path=None,
        )


def test_load_and_validate_problem_requires_units(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path, characters=("alice",))

    storage = FileStorage()
    with pytest.raises(ValidationError, match="Provide either units or units_file"):
        load_and_validate_problem(
            storage,
            dataset_path,
            roster_path=None,
            units_str=None,
            units_file_path=None,
            whitelist_path=None,
            blacklist_path=None,
        )


def test_load_and_validate_problem_rejects_both_units_inputs(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path, characters=("alice",))
    units_path = tmp_path / "units.json"
    units_path.write_text("[1]")

    storage = FileStorage()
    with pytest.raises(ValidationError, match="either units or units_file"):
        load_and_validate_problem(
            storage,
            dataset_path,
            roster_path=None,
            units_str="1",
            units_file_path=units_path,
            whitelist_path=None,
            blacklist_path=None,
        )


def test_load_and_validate_problem_rejects_invalid_whitelist(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path, characters=("alice", "bob"))
    roster_path = tmp_path / "roster.csv"
    roster_path.write_text("id\nalice\nbob\n")
    whitelist_path = tmp_path / "whitelist.csv"
    whitelist_path.write_text("alice,zoe\n")

    storage = FileStorage()
    with pytest.raises(ValidationError, match="Whitelist pair contains missing"):
        load_and_validate_problem(
            storage,
            dataset_path,
            roster_path=roster_path,
            units_str="2",
            units_file_path=None,
            whitelist_path=whitelist_path,
            blacklist_path=None,
        )


def test_load_and_validate_problem_rejects_invalid_rapport(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(
        dataset_path,
        characters=("alice", "bob", "charlie"),
        rapports=[
            {"id": "alice", "pairs": ["bob"]},
            {"id": "bob", "pairs": ["alice"]},
        ],
    )
    roster_path = tmp_path / "roster.csv"
    roster_path.write_text("id\nalice\nbob\ncharlie\n")
    whitelist_path = tmp_path / "whitelist.csv"
    whitelist_path.write_text("alice,charlie\n")

    storage = FileStorage()
    with pytest.raises(ValidationError, match="Whitelist pair is not a valid rapport"):
        load_and_validate_problem(
            storage,
            dataset_path,
            roster_path=roster_path,
            units_str="2",
            units_file_path=None,
            whitelist_path=whitelist_path,
            blacklist_path=None,
        )


def test_load_and_validate_problem_defaults_roster_to_character_set(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path, characters=("bob", "alice"))

    storage = FileStorage()
    inputs, _warnings = load_and_validate_problem(
        storage,
        dataset_path,
        roster_path=None,
        units_str="2",
        units_file_path=None,
        whitelist_path=None,
        blacklist_path=None,
    )

    assert inputs.roster_ids == ["alice", "bob"]


def test_load_combat_context_warns_on_missing_character_classes(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(
        dataset_path,
        characters=("alice",),
        classes=[_class_definition()],
    )
    storage = FileStorage()
    dataset = storage.load_dataset(dataset_path)

    _, warnings, diagnostics = load_combat_context(
        storage,
        dataset,
        roster_set={"alice"},
        combat_scoring_path=None,
        character_classes_path=None,
    )

    assert len(warnings) == 1
    assert "dataset character classes are empty" in warnings[0].message
    assert diagnostics == []


def test_load_combat_context_rejects_unknown_override_character(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(
        dataset_path,
        characters=("alice",),
        classes=[_class_definition()],
        character_classes={"alice": {"default_class": "warrior", "class_line": None}},
    )
    overrides_path = tmp_path / "character_classes.csv"
    overrides_path.write_text("zoe,warrior\n")
    storage = FileStorage()
    dataset = storage.load_dataset(dataset_path)

    with pytest.raises(ValidationError, match="unknown ids"):
        load_combat_context(
            storage,
            dataset,
            roster_set={"alice"},
            combat_scoring_path=None,
            character_classes_path=overrides_path,
        )


def test_load_combat_context_rejects_unknown_override_class(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(
        dataset_path,
        characters=("alice",),
        classes=[_class_definition()],
        character_classes={"alice": {"default_class": "warrior", "class_line": None}},
    )
    overrides_path = tmp_path / "character_classes.csv"
    overrides_path.write_text("alice,mage\n")
    storage = FileStorage()
    dataset = storage.load_dataset(dataset_path)

    with pytest.raises(ValidationError, match="unknown classes"):
        load_combat_context(
            storage,
            dataset,
            roster_set={"alice"},
            combat_scoring_path=None,
            character_classes_path=overrides_path,
        )


def test_load_combat_context_emits_missing_defaults_diagnostic(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(
        dataset_path,
        characters=("alice", "bob"),
        classes=[_class_definition()],
        character_classes={"alice": {"default_class": "warrior", "class_line": None}},
    )
    storage = FileStorage()
    dataset = storage.load_dataset(dataset_path)

    _, warnings, diagnostics = load_combat_context(
        storage,
        dataset,
        roster_set={"alice", "bob"},
        combat_scoring_path=None,
        character_classes_path=None,
    )

    assert warnings == []
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "missing_default_classes"


def test_apply_preset_updates_scoring() -> None:
    scoring = CombatScoringConfig()
    updated = apply_preset(scoring, "offensive")

    assert updated.coverage.assist_type_weights["ranged"] == 1.0
    assert updated.coverage.unit_type_weights["flying"] == 0.8
    assert updated.diversity.unique_leader_bonus == 0.8
    assert scoring.coverage.assist_type_weights["ranged"] == 0.5


def test_apply_preset_rejects_unknown() -> None:
    with pytest.raises(ValidationError, match="Unknown preset"):
        apply_preset(CombatScoringConfig(), "unknown")


def test_make_combat_score_fn_returns_none_without_classes() -> None:
    dataset = Dataset(characters=[Character(id="alice", name=None)], rapports=[])
    score_fn = make_combat_score_fn(dataset, {}, CombatScoringConfig())
    assert score_fn is None


def test_make_combat_score_fn_scores_units() -> None:
    class_def = ClassDefinition.model_validate(_class_definition())
    dataset = Dataset(
        characters=[Character(id="alice", name=None)],
        rapports=[],
        classes=[class_def],
        character_classes={
            "alice": CharacterClassInfo(default_class="warrior", class_line=None)
        },
    )
    scoring = CombatScoringConfig(role_weights={"frontline": 1.0})
    score_fn = make_combat_score_fn(dataset, {"alice": "warrior"}, scoring)

    assert score_fn is not None
    assert score_fn([["alice"]]) == 1.0


def test_run_solve_requires_combat_data_for_min_score(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path, characters=("alice",))
    storage = FileStorage()

    with pytest.raises(ValidationError, match="Minimum combat score requires"):
        run_solve(
            storage=storage,
            dataset_path=dataset_path,
            roster_path=None,
            units_str="1",
            units_file_path=None,
            whitelist_path=None,
            blacklist_path=None,
            combat_scoring_path=None,
            character_classes_path=None,
            seed=0,
            restarts=1,
            swap_iterations=1,
            min_combat_score=1.0,
        )


def test_run_solve_computes_empty_combat_summary_without_classes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path, characters=("alice", "bob"))
    roster_path = tmp_path / "roster.csv"
    roster_path.write_text("id\nalice\nbob\n")

    def fake_solve(*_args: object, **_kwargs: object) -> Solution:
        return Solution(
            units=[["alice", "bob"]],
            unit_rapports=[1],
            total_rapports=1,
            unassigned=[],
            seed=0,
            restarts=1,
            swap_iterations=1,
            combat=None,
        )

    monkeypatch.setattr("unicorn_armada.core.solve", fake_solve)
    storage = FileStorage()

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

    assert result.solution.combat is not None
    assert result.solution.combat.total_score == 0.0
    assert result.solution.combat.unit_scores == [0.0]


def test_run_benchmark_without_combat_data_reports_missing(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path, characters=("alice", "bob"))
    roster_path = tmp_path / "roster.csv"
    roster_path.write_text("id\nalice\nbob\n")
    storage = FileStorage()

    result = run_benchmark(
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
        trials=1,
        unit_samples=1,
    )

    assert result.report.combat_available is False
    assert "Combat data: missing" in result.summary_lines[1]
    assert "Combat data missing; scores default to 0." in result.summary_lines


def test_run_benchmark_with_combat_data_uses_samples(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(
        dataset_path,
        characters=("alice", "bob"),
        classes=[_class_definition()],
        character_classes={
            "alice": {"default_class": "warrior", "class_line": None},
            "bob": {"default_class": "warrior", "class_line": None},
        },
    )
    roster_path = tmp_path / "roster.csv"
    roster_path.write_text("id\nalice\nbob\n")

    def fake_sample_unit_scores(*_args: object, **_kwargs: object) -> list[float]:
        return [1.0]

    def fake_generate_random_assignment(
        *_args: object, **_kwargs: object
    ) -> list[list[str]]:
        return [["alice", "bob"]]

    monkeypatch.setattr(
        "unicorn_armada.core.sample_unit_scores", fake_sample_unit_scores
    )
    monkeypatch.setattr(
        "unicorn_armada.core.generate_random_assignment",
        fake_generate_random_assignment,
    )

    storage = FileStorage()
    result = run_benchmark(
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
        trials=1,
        unit_samples=1,
    )

    assert result.report.combat_available is True
    assert result.report.sample_counts.total_successes == 1
