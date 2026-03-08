# References for CLI/Core test coverage push

## Similar Implementations

### CLI summary unit tests

- **Location:** `tests/unit/test_cli.py`
- **Relevance:** Existing unit test style for CLI output helpers.
- **Key patterns:** tmp_path usage for output verification, direct assertions.

### Core validation unit tests

- **Location:** `tests/unit/test_core.py`
- **Relevance:** Existing core workflow coverage and data fixtures.
- **Key patterns:** minimal dataset setup, FileStorage usage, targeted assertions.

### Integration test configuration

- **Location:** `tests/integration/conftest.py`
- **Relevance:** Integration tier markers and timing requirements.
- **Key patterns:** autouse markers for `integration` and timeout.

### CLI command implementation

- **Location:** `src/unicorn_armada/cli.py`
- **Relevance:** Command wiring, error handling, output writes.
- **Key patterns:** run_* delegation, Typer error mapping, structured logging.

### Core business logic implementation

- **Location:** `src/unicorn_armada/core.py`
- **Relevance:** Validation, combat context loading, solve/benchmark workflows.
- **Key patterns:** warnings/diagnostics, preset application, combat scoring gates.
