# CLI Core Logic Extraction — Plan

Goal: Complete the roadmap item to extract business logic from the CLI into the core domain while keeping the current `src/unicorn_armada` layout. The CLI should remain a thin adapter that parses args, invokes core APIs, and formats output.

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-01-27-1407-cli-core-logic-extraction/` with:

- `plan.md` — This plan
- `shape.md` — Shaping notes (scope, decisions, context)
- `standards.md` — Relevant standards that apply to this work
- `references.md` — Pointers to similar code
- `visuals/` — (Empty; no visuals provided)

## Task 2: Define core domain APIs for CLI workflows

- Add or update core models for CLI-facing workflows (solve, benchmark, sync).
- Represent warnings/diagnostics as typed core data instead of printing in CLI.
- Keep naming consistent with existing module conventions and CLI command names.

## Task 3: Move input loading and validation into core

- Consolidate `load_problem_inputs` into core using `load_and_validate_problem` as the base.
- Move combat context validation and missing-default-class checks into core.
- Core should accept `StorageProtocol` and return typed data and diagnostics.

## Task 4: Move orchestration logic into core

- Extract solve workflow: build combat scorer, call solver, compute combat summary, return model.
- Extract benchmark workflow: compute stats/report, return API response data and summary lines.
- Extract rapport sync workflow: normalize entries, return updated dataset and stats.

## Task 5: Thin CLI adapter updates

- CLI parses args only, calls core APIs, and maps core errors to `typer.BadParameter`.
- CLI performs file I/O and console output using core results.
- Preserve output formats and error messages.

## Task 6: Tests and parity checks

- Update or add unit tests for new core APIs (`tests/unit/test_core.py`).
- Adjust CLI tests to reflect thin adapter behavior if needed.
- Verify CLI outputs remain unchanged for existing inputs.

## Out of Scope

- Repository layout change to `packages/` and `services/`.
- New TUI or API surface.
- New logging or storage adapters beyond existing `FileStorage`.
