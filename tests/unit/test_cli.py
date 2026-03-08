"""Unit tests for CLI module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import typer

if TYPE_CHECKING:
    from pathlib import Path

import unicorn_armada.cli as cli_module
from unicorn_armada.cli import (
    benchmark_units,
    solve_units,
    sync_rapports,
    write_detailed_combat_summary,
    write_summary,
)
from unicorn_armada.io import InputError
from unicorn_armada.models import (
    BenchmarkInputSummary,
    BenchmarkReport,
    BenchmarkRunResult,
    BenchmarkSampleCounts,
    BenchmarkStatsSummary,
    CombatDiagnostic,
    CombatScoringConfig,
    CombatSummary,
    CombatUnitBreakdown,
    RapportListEntry,
    RapportSyncResult,
    RapportSyncStats,
    Solution,
    SolveRunResult,
    UnitSizeReport,
    UserMessage,
)

# --- Fixtures ---


@pytest.fixture
def sample_solution() -> Solution:
    """Sample solution for testing."""
    return Solution(
        units=[["alice", "bob", "charlie"], ["dave", "eve"]],
        unit_rapports=[3, 1],
        total_rapports=4,
        unassigned=[],
        seed=0,
        restarts=50,
        swap_iterations=200,
        combat=CombatSummary(
            unit_scores=[3.0, 1.5],
            unit_breakdowns=[
                CombatUnitBreakdown(
                    roles={"frontline": 1, "support": 1},
                    capabilities={"archer": 1, "assist": 1},
                    unknown_members=[],
                    score=3.0,
                ),
                CombatUnitBreakdown(
                    roles={"backline": 1},
                    capabilities={"caster": 1},
                    unknown_members=[],
                    score=1.5,
                ),
            ],
            total_score=4.5,
        ),
    )


@pytest.fixture
def sample_combat_scoring() -> CombatScoringConfig:
    """Sample combat scoring config for testing."""
    return CombatScoringConfig(
        role_weights={"frontline": 1.0, "support": 1.0, "backline": 1.0},
        capability_weights={"archer": 0.5, "caster": 0.5, "assist": 0.5},
    )


# --- Tests for write_summary ---


class TestWriteSummary:
    """Tests for write_summary function."""

    def test_basic_summary(
        self,
        sample_solution: Solution,
        tmp_path: Path,
    ) -> None:
        """Basic summary should write without combat breakdown."""
        output_path = tmp_path / "summary.txt"
        write_summary(output_path, sample_solution, [3, 2], combat_summary=False)

        content = output_path.read_text()
        assert "Total rapports: 4" in content
        assert "Total combat score: 4.50" in content
        assert "Unit 1 (3 slots): 3 rapports, 3.00 combat" in content
        assert "Unit 2 (2 slots): 1 rapports, 1.50 combat" in content
        assert "alice, bob, charlie" in content
        assert "dave, eve" in content
        assert "## Combat Summary Breakdown" not in content

    def test_combat_summary_flag(
        self,
        sample_solution: Solution,
        sample_combat_scoring: CombatScoringConfig,
        tmp_path: Path,
    ) -> None:
        """Combat summary flag should append detailed breakdown."""
        output_path = tmp_path / "summary.txt"
        write_summary(
            output_path,
            sample_solution,
            [3, 2],
            combat_summary=True,
            combat_scoring=sample_combat_scoring,
        )

        content = output_path.read_text()
        assert "Total rapports: 4" in content
        assert "## Combat Summary Breakdown" in content
        assert "Unit 1 (3.00 combat):" in content
        assert "  Roles: frontline, support" in content
        assert "  Capabilities: archer, assist" in content
        assert "Unit 2 (1.50 combat):" in content
        assert "  Roles: backline" in content
        assert "  Capabilities: caster" in content

    def test_combat_summary_flag_without_combat_scoring(
        self,
        sample_solution: Solution,
        tmp_path: Path,
    ) -> None:
        """Combat summary flag without scoring config should not append breakdown."""
        output_path = tmp_path / "summary.txt"
        write_summary(
            output_path,
            sample_solution,
            [3, 2],
            combat_summary=True,
            combat_scoring=None,
        )

        content = output_path.read_text()
        assert "Total rapports: 4" in content
        assert "## Combat Summary Breakdown" not in content

    def test_combat_summary_flag_without_solution_combat(
        self,
        tmp_path: Path,
    ) -> None:
        """Combat summary flag without solution.combat should not append breakdown."""
        solution = Solution(
            units=[["alice", "bob", "charlie"], ["dave", "eve"]],
            unit_rapports=[3, 1],
            total_rapports=4,
            unassigned=[],
            seed=0,
            restarts=50,
            swap_iterations=200,
            combat=None,
        )
        output_path = tmp_path / "summary.txt"
        write_summary(
            output_path,
            solution,
            [3, 2],
            combat_summary=True,
            combat_scoring=CombatScoringConfig(),
        )

        content = output_path.read_text()
        assert "Total rapports: 4" in content
        assert "## Combat Summary Breakdown" not in content

    def test_summary_with_unassigned(
        self,
        tmp_path: Path,
    ) -> None:
        """Summary should list unassigned characters."""
        solution = Solution(
            units=[["alice", "bob"]],
            unit_rapports=[1],
            total_rapports=1,
            unassigned=["charlie", "dave"],
            seed=0,
            restarts=50,
            swap_iterations=200,
            combat=None,
        )
        output_path = tmp_path / "summary.txt"
        write_summary(output_path, solution, [2], combat_summary=False)

        content = output_path.read_text()
        assert "Unassigned:" in content
        assert "charlie, dave" in content

    def test_summary_with_empty_unit(
        self,
        tmp_path: Path,
    ) -> None:
        """Summary should show empty units correctly."""
        solution = Solution(
            units=[[]],
            unit_rapports=[0],
            total_rapports=0,
            unassigned=[],
            seed=0,
            restarts=50,
            swap_iterations=200,
            combat=None,
        )
        output_path = tmp_path / "summary.txt"
        write_summary(output_path, solution, [2], combat_summary=False)

        content = output_path.read_text()
        assert "Unit 1 (2 slots): 0 rapports" in content
        assert "(empty)" in content


# --- Tests for write_detailed_combat_summary ---


class TestWriteDetailedCombatSummary:
    """Tests for write_detailed_combat_summary function."""

    def test_appends_to_existing_file(
        self,
        sample_solution: Solution,
        sample_combat_scoring: CombatScoringConfig,
        tmp_path: Path,
    ) -> None:
        """Detailed summary should append to existing file."""
        output_path = tmp_path / "summary.txt"
        output_path.write_text("Existing content\n")

        write_detailed_combat_summary(
            output_path, sample_solution, [3, 2], sample_combat_scoring
        )

        content = output_path.read_text()
        assert content.startswith("Existing content\n")
        assert "## Combat Summary Breakdown" in content

    def test_displays_roles_and_capabilities(
        self,
        sample_solution: Solution,
        sample_combat_scoring: CombatScoringConfig,
        tmp_path: Path,
    ) -> None:
        """Detailed summary should display roles and capabilities correctly."""
        output_path = tmp_path / "summary.txt"
        output_path.write_text("")  # Empty file

        write_detailed_combat_summary(
            output_path, sample_solution, [3, 2], sample_combat_scoring
        )

        content = output_path.read_text()
        assert "Unit 1 (3.00 combat):" in content
        assert "  Roles: frontline, support" in content
        assert "  Capabilities: archer, assist" in content
        assert "Unit 2 (1.50 combat):" in content
        assert "  Roles: backline" in content
        assert "  Capabilities: caster" in content

    def test_handles_empty_roles_and_capabilities(
        self,
        tmp_path: Path,
    ) -> None:
        """Detailed summary should handle empty roles and capabilities."""
        solution = Solution(
            units=[["alice"]],
            unit_rapports=[0],
            total_rapports=0,
            unassigned=[],
            seed=0,
            restarts=50,
            swap_iterations=200,
            combat=CombatSummary(
                unit_scores=[0.0],
                unit_breakdowns=[
                    CombatUnitBreakdown(
                        roles={},
                        capabilities={},
                        unknown_members=[],
                        score=0.0,
                    )
                ],
                total_score=0.0,
            ),
        )
        output_path = tmp_path / "summary.txt"
        output_path.write_text("")

        write_detailed_combat_summary(output_path, solution, [1], CombatScoringConfig())

        content = output_path.read_text()
        assert "Unit 1 (0.00 combat):" in content
        assert "  Roles: (none)" in content
        assert "  Capabilities: (none)" in content


class DummyLogger:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def info(self, *_args: object, **_kwargs: object) -> None:
        pass

    def warn(self, *_args: object, **_kwargs: object) -> None:
        pass

    def error(self, *_args: object, **_kwargs: object) -> None:
        pass


@pytest.fixture
def quiet_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "Logger", DummyLogger)


class TestSolveUnits:
    def test_writes_outputs_and_emits_messages(
        self,
        sample_solution: Solution,
        sample_combat_scoring: CombatScoringConfig,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        quiet_logger: None,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        warnings = [
            UserMessage(severity="warning", message="watch out"),
            UserMessage(severity="info", message="heads up"),
        ]
        diagnostics = [
            CombatDiagnostic(
                code="missing_default_classes",
                severity="warning",
                message="missing default classes for roster characters: alice",
                subject=None,
            ),
            CombatDiagnostic(
                code="unknown_class_id",
                severity="error",
                message="Character 'alice' has unknown class 'mage'",
                subject="alice",
            ),
        ]
        result = SolveRunResult(
            solution=sample_solution,
            unit_sizes=[3, 2],
            combat_scoring=sample_combat_scoring,
            warnings=warnings,
            combat_diagnostics=diagnostics,
        )
        called: dict[str, object] = {}

        def fake_run_solve(**kwargs: object) -> SolveRunResult:
            called.update(kwargs)
            return result

        monkeypatch.setattr(cli_module, "run_solve", fake_run_solve)

        out_path = tmp_path / "solution.json"
        summary_path = tmp_path / "summary.txt"

        solve_units(
            dataset=tmp_path / "dataset.json",
            roster=tmp_path / "roster.csv",
            units="3,2",
            units_file=None,
            whitelist=None,
            blacklist=None,
            seed=7,
            restarts=1,
            swap_iterations=2,
            min_combat_score=None,
            out=out_path,
            summary=summary_path,
            combat_summary=True,
        )

        output = capsys.readouterr().out
        assert "Warning: watch out" in output
        assert "heads up" in output
        assert "Warning: missing default classes for roster characters: alice" in output
        assert "Character 'alice' has unknown class 'mage'" in output
        assert "Total rapports: 4" in output
        assert f"Wrote solution to {out_path}" in output
        assert f"Wrote summary to {summary_path}" in output

        assert out_path.exists() is True
        summary_contents = summary_path.read_text()
        assert "Total rapports: 4" in summary_contents
        assert "## Combat Summary Breakdown" in summary_contents

        assert called["units_str"] == "3,2"
        assert called["dataset_path"] == tmp_path / "dataset.json"
        assert called["roster_path"] == tmp_path / "roster.csv"
        assert called["seed"] == 7
        assert called["restarts"] == 1
        assert called["swap_iterations"] == 2

    def test_maps_validation_error_to_bad_parameter(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        quiet_logger: None,
    ) -> None:
        def fake_run_solve(**_kwargs: object) -> SolveRunResult:
            raise cli_module.ValidationError("bad input")

        monkeypatch.setattr(cli_module, "run_solve", fake_run_solve)

        with pytest.raises(typer.BadParameter, match="bad input"):
            solve_units(
                dataset=tmp_path / "dataset.json",
                roster=None,
                units="2",
                units_file=None,
                whitelist=None,
                blacklist=None,
                seed=0,
                restarts=1,
                swap_iterations=1,
                min_combat_score=None,
                out=tmp_path / "solution.json",
                summary=tmp_path / "summary.txt",
                combat_summary=False,
            )


class TestBenchmarkUnits:
    def test_writes_outputs_and_emits_messages(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        quiet_logger: None,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        stats = BenchmarkStatsSummary(
            count=1,
            min=1.0,
            max=1.0,
            mean=1.0,
            p50=1.0,
            p75=1.0,
            p90=1.0,
            std=0.0,
        )
        report = BenchmarkReport(
            combat_available=True,
            inputs=BenchmarkInputSummary(seed=0, units=[2], trials=1, unit_samples=1),
            sample_counts=BenchmarkSampleCounts(
                total_trials=1, total_successes=1, total_failures=0
            ),
            total_score_stats=stats,
            recommended_min_total=1.0,
            recommended_strict_total=1.0,
            per_unit_size={
                "2": UnitSizeReport(
                    stats=stats,
                    recommended_min=1.0,
                    recommended_strict=1.0,
                    samples=1,
                )
            },
        )
        result = BenchmarkRunResult(
            report=report,
            summary_lines=["line one", "line two"],
            warnings=[
                UserMessage(severity="warning", message="be careful"),
                UserMessage(severity="info", message="all good"),
            ],
            combat_diagnostics=[
                CombatDiagnostic(
                    code="unknown_class_id",
                    severity="error",
                    message="Character 'alice' has unknown class 'mage'",
                    subject="alice",
                )
            ],
        )
        called: dict[str, object] = {}

        def fake_run_benchmark(**kwargs: object) -> BenchmarkRunResult:
            called.update(kwargs)
            return result

        monkeypatch.setattr(cli_module, "run_benchmark", fake_run_benchmark)

        out_path = tmp_path / "benchmark.json"
        summary_path = tmp_path / "benchmark.txt"

        benchmark_units(
            dataset=tmp_path / "dataset.json",
            roster=tmp_path / "roster.csv",
            units="2",
            units_file=None,
            whitelist=None,
            blacklist=None,
            seed=0,
            trials=1,
            unit_samples=1,
            out=out_path,
            summary=summary_path,
        )

        output = capsys.readouterr().out
        assert "Warning: be careful" in output
        assert "all good" in output
        assert "Character 'alice' has unknown class 'mage'" in output
        assert f"Wrote benchmark to {out_path}" in output
        assert f"Wrote benchmark summary to {summary_path}" in output

        assert out_path.exists() is True
        assert summary_path.read_text() == "line one\nline two\n"
        assert called["units_str"] == "2"
        assert called["trials"] == 1
        assert called["unit_samples"] == 1

    def test_maps_input_error_to_bad_parameter(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        quiet_logger: None,
    ) -> None:
        def fake_run_benchmark(**_kwargs: object) -> BenchmarkRunResult:
            raise InputError("bad input")

        monkeypatch.setattr(cli_module, "run_benchmark", fake_run_benchmark)

        with pytest.raises(typer.BadParameter, match="bad input"):
            benchmark_units(
                dataset=tmp_path / "dataset.json",
                roster=None,
                units="2",
                units_file=None,
                whitelist=None,
                blacklist=None,
                seed=0,
                trials=1,
                unit_samples=1,
                out=tmp_path / "benchmark.json",
                summary=tmp_path / "benchmark.txt",
            )


class TestSyncRapports:
    def test_no_changes_skips_dataset_write(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        quiet_logger: None,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        dataset_path = tmp_path / "dataset.json"
        dataset_path.write_text(
            '{"characters":[{"id":"alice"},{"id":"bob"}],'
            '"rapports":[{"id":"alice","pairs":["bob"]},'
            '{"id":"bob","pairs":["alice"]}]}'
        )

        result = RapportSyncResult(
            normalized=[
                RapportListEntry(id="alice", pairs=["bob"]),
                RapportListEntry(id="bob", pairs=["alice"]),
            ],
            stats=RapportSyncStats(
                added_pairs=0,
                added_entries=0,
                duplicate_entries=0,
                skipped_self=0,
                skipped_unknown=0,
                unknown_entry_ids=0,
            ),
            changed=False,
        )

        def fake_run_sync_rapports(
            *_args: object, **_kwargs: object
        ) -> RapportSyncResult:
            return result

        monkeypatch.setattr(cli_module, "run_sync_rapports", fake_run_sync_rapports)

        report_path = tmp_path / "report.json"
        sync_rapports(dataset=dataset_path, out=None, report=report_path)

        output = capsys.readouterr().out
        assert "Rapports already bidirectional" in output
        assert report_path.exists() is True

    def test_writes_dataset_and_report_on_changes(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        quiet_logger: None,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        dataset_path = tmp_path / "dataset.json"
        dataset_path.write_text(
            '{"characters":[{"id":"alice"},{"id":"bob"}],'
            '"rapports":[{"id":"alice","pairs":["bob"]}]}'
        )

        result = RapportSyncResult(
            normalized=[
                RapportListEntry(id="alice", pairs=["bob"]),
                RapportListEntry(id="bob", pairs=["alice"]),
            ],
            stats=RapportSyncStats(
                added_pairs=1,
                added_entries=1,
                duplicate_entries=0,
                skipped_self=0,
                skipped_unknown=0,
                unknown_entry_ids=0,
            ),
            changed=True,
        )

        def fake_run_sync_rapports(
            *_args: object, **_kwargs: object
        ) -> RapportSyncResult:
            return result

        monkeypatch.setattr(cli_module, "run_sync_rapports", fake_run_sync_rapports)

        out_path = tmp_path / "updated.json"
        report_path = tmp_path / "report.json"
        sync_rapports(dataset=dataset_path, out=out_path, report=report_path)

        output = capsys.readouterr().out
        assert f"Wrote cleaned dataset to {out_path}" in output
        assert "Added 1 reciprocal pairs." in output
        assert report_path.exists() is True
        assert out_path.exists() is True

    def test_missing_dataset_raises_bad_parameter(
        self,
        tmp_path: Path,
        quiet_logger: None,
    ) -> None:
        missing_path = tmp_path / "missing.json"
        with pytest.raises(typer.BadParameter, match="Dataset not found"):
            sync_rapports(
                dataset=missing_path, out=None, report=tmp_path / "report.json"
            )
