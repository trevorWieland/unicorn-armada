# References for Scoring Normalization Layer + Feature Registry

## Similar Implementations

### Combat Scoring Pipeline
- **Location:** `src/unicorn_armada/combat.py`
- **Relevance:** Current scoring flow (unit tags, coverage, diversity).
- **Key patterns:** Count tags per unit, compute coverage/diversity summaries.

### Combat Models
- **Location:** `src/unicorn_armada/models.py`
- **Relevance:** Class definitions, scoring configs, and summary schemas.
- **Key patterns:** Normalization validators, Pydantic models, summary fields.

### Combat Context Loading
- **Location:** `src/unicorn_armada/core.py`
- **Relevance:** Effective class mapping, preset application.
- **Key patterns:** Input validation, default config layering.

### CLI Combat Flow
- **Location:** `src/unicorn_armada/cli.py`
- **Relevance:** Warnings, summary output, and combat scoring call sites.
- **Key patterns:** Thin adapter behavior, warning messaging.

### Default Scoring Config
- **Location:** `config/combat_scoring.json`
- **Relevance:** Default weights and feature toggles.
- **Key patterns:** Config-driven scoring behavior.

### Combat Tests
- **Location:** `tests/unit/test_combat.py`
- **Relevance:** Expected scoring behavior and error cases.
- **Key patterns:** Unit score, coverage, and diversity assertions.
