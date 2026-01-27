# CLI Core Logic Extraction — Shaping Notes

## Scope

- Extract business logic from `src/unicorn_armada/cli.py` into core domain functions.
- Keep the current `src/unicorn_armada` layout, but shape APIs to allow a later `packages/` + `services/` split.
- Ensure the CLI becomes a thin adapter: parse args, call core APIs, format outputs.

## Decisions

- Keep repository layout unchanged for this refactor.
- Use `StorageProtocol` with `FileStorage` to keep I/O in the CLI and make core reusable.
- Preserve existing CLI output formats and error messages.
- Represent diagnostics as typed core data, not `typer.echo` inside core.

## Context

- **Visuals:** None
- **References:** `src/unicorn_armada/cli.py`, `src/unicorn_armada/core.py`, `src/unicorn_armada/io.py`, `src/unicorn_armada/protocols.py`
- **Product alignment:** Keep CLI-first UX; future TUI should be able to reuse core logic without duplication.

## Standards Applied

- architecture/thin-adapter-pattern — CLI should be a thin wrapper over core APIs.
- architecture/adapter-interface-protocol — Use protocol interfaces for storage and I/O.
- architecture/naming-conventions — Keep module/function/class naming consistent.
- python/strict-typing-enforcement — No `Any`/`object`; explicit types for core APIs and models.
