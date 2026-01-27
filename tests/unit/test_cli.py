"""Unit tests for CLI module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from unicorn_armada.cli import write_detailed_combat_summary, write_summary
from unicorn_armada.models import (
    CombatScoringConfig,
    CombatSummary,
    CombatUnitBreakdown,
    Solution,
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
