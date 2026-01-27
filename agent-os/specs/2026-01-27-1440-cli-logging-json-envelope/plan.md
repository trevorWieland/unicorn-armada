# Plan: CLI Structured Logging + JSON Envelope

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-01-27-1440-cli-logging-json-envelope/` with:

- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context)
- **standards.md** — Relevant standards
- **references.md** — Reference implementations studied
- **visuals/** — Any mockups or screenshots (none provided)

## Task 2: Structured Logging in CLI Commands

- Add structured JSONL logging to CLI commands in `src/unicorn_armada/cli.py`.
- Create a per-command `Logger` with a run-scoped `run_id`.
- Emit log events for:
  - `run_started` (command + inputs)
  - `data_loaded` / `data_validated`
  - `warning` conditions (log level `warn`)
  - `data_written` (output paths)
  - `run_completed` / `run_failed`
- Keep `typer.echo` output for user-facing text (logs on stderr).

## Task 3: API Response Envelope for JSON Outputs

- Wrap `solve-units` JSON output (`out/solution.json`) in `APIResponse.success`.
- Keep `benchmark-units` JSON output enveloped and ensure consistent formatting.
- Keep dataset output for `sync-rapports` raw (dataset schema unchanged).
- Add a new JSON report output for `sync-rapports` using the envelope:
  - Path: `out/sync-rapports.json`
  - Payload: stats + changed flag + output path

## Task 4: Documentation Updates

- Update `README.md` to show the response envelope for JSON outputs.
- Document that CLI emits structured JSONL logs to stderr.
- Describe the new `out/sync-rapports.json` report file and contents.

---

Plan complete. When you approve and execute:

1. Task 1 will save all spec documentation first
2. Then implementation tasks will proceed
