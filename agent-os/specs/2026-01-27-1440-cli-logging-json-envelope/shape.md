# CLI Structured Logging + JSON Envelope — Shaping Notes

## Scope

Add structured JSONL logging to all CLI commands and ensure all JSON outputs use
the `{data, error, meta}` API response envelope. Keep the CLI thin and preserve
the raw dataset format for `sync-rapports` while adding a separate report output.

## Decisions

- Use the existing `Logger` in `src/unicorn_armada/logging.py` for JSONL logs.
- Emit logs to stderr so user-facing stdout output remains unchanged.
- Use a per-command `run_id` shared across log lines.
- Wrap `solve-units` and `benchmark-units` JSON outputs with `APIResponse`.
- Keep `sync-rapports` dataset output raw; add `out/sync-rapports.json` report
  with envelope containing summary stats and output path.
- Keep CLI as a thin adapter over core logic.

## Context

- **Visuals:** None
- **References:**
  - `src/unicorn_armada/cli.py`
  - `src/unicorn_armada/logging.py`
  - `src/unicorn_armada/responses.py`
- **Product alignment:** Align with mission (accurate unit composition output)
  and CLI-first stack (Typer + Pydantic).

## Standards Applied

- architecture/api-response-format — ensures consistent JSON envelope outputs
- architecture/log-line-format — JSONL schema for structured logs
- architecture/thin-adapter-pattern — CLI remains a surface adapter
