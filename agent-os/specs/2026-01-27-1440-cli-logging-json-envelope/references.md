# References for CLI Structured Logging + JSON Envelope

## Similar Implementations

### CLI commands

- **Location:** `src/unicorn_armada/cli.py`
- **Relevance:** Current command implementations and JSON output handling.
- **Key patterns:** Typer command structure, output file writes, benchmark envelope usage.

### Structured logging

- **Location:** `src/unicorn_armada/logging.py`
- **Relevance:** JSONL logger and standard event names.
- **Key patterns:** `Logger` class, `LogEntry` schema, event constants.

### API response envelope

- **Location:** `src/unicorn_armada/responses.py`
- **Relevance:** Pydantic envelope for JSON outputs.
- **Key patterns:** `APIResponse.success`/`failure`, error codes, metadata.
