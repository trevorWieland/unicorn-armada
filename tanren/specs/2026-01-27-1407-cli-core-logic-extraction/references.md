# References for CLI Core Logic Extraction

## Similar Implementations

### CLI orchestration and validation

- **Location:** `src/unicorn_armada/cli.py`
- **Relevance:** Current CLI logic to extract into core (input validation, orchestration, output formatting).
- **Key patterns:** Typer options/commands, error translation to `typer.BadParameter`, summary writing.

### Core domain entry points

- **Location:** `src/unicorn_armada/core.py`
- **Relevance:** Existing core utilities (validation, combat context, scoring presets) to extend.
- **Key patterns:** ValidationError, `load_and_validate_problem`, `load_combat_context`, pure logic helpers.

### IO and storage adapter

- **Location:** `src/unicorn_armada/io.py`
- **Relevance:** File-based loader functions and `FileStorage` implementation for protocol injection.
- **Key patterns:** InputError mapping, storage facade methods.

### Protocol interfaces

- **Location:** `src/unicorn_armada/protocols.py`
- **Relevance:** Protocol definitions to enforce thin-adapter + dependency injection.
- **Key patterns:** `StorageProtocol` and related loader/writer protocols.

### CLI tests

- **Location:** `tests/unit/test_cli.py`
- **Relevance:** Output and summary formatting expectations to preserve.
- **Key patterns:** Summary content assertions, combat breakdown formatting.
