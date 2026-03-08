# Standards for Enhanced Combat Summary

The following standards apply to this work.

---

## python/modern-python-314

Use Python 3.14 features and patterns. Avoid legacy constructs.

```python
# ✓ Good: Modern Python 3.14
# Type unions (Python 3.10+)
result: str | None

# Pattern matching (Python 3.10+)
match phase:
    case "translate":
        await translate()
    case "qa":
        await run_qa()
    case _:
        raise ValueError(f"Unknown phase: {phase}")

# Dictionary union operators (Python 3.9+)
config = base_config | custom_config

# f-string debugging (Python 3.8+)
print(f"{result=}")  # Prints: result='value'

# Async generators (Python 3.6+)
async def stream_translations():
    for scene in scenes:
        yield await translate_scene(scene)

# ✗ Bad: Legacy patterns
result: Optional[str]  # Old-style Union

if phase == "translate":
    await translate()
elif phase == "qa":
    await run_qa()
else:
    raise ValueError(f"Unknown phase: {phase}")  # No pattern matching

config = {**base_config, **custom_config}  # Old unpacking

print(f"result={result}")  # No f-string debugging

def stream_translations():  # Blocking generator
    for scene in scenes:
        yield translate_scene(scene)
```

**Modern Python 3.14 features to use:**
- Type unions: `str | None` instead of `Union[str, None]`
- Pattern matching: `match/case` instead of if/elif chains
- Dictionary union: `dict1 | dict2` instead of unpacking
- f-string debugging: `f"{var=}"` instead of `f"var={var}"`
- Walrus operator: `if (match := pattern.search(text)):` for assignment in expressions
- Async generators: `async def` and `async for`
- Context managers: `with` statements for resource management
- Dataclass improvements: `dataclass_transform` and field parameters

**Legacy patterns to avoid:**
- `Optional[T]`, `Union[T, U]` - use `T | None`, `T | U`
- `if/elif/else` chains for type/state - use `match/case`
- `{**d1, **d2}` - use `d1 | d2`
- `f"var={var}"` - use `f"{var=}"`
- `typing.List`, `typing.Dict` - use built-in `list`, `dict`
- `yield` without `async` - use async generators where appropriate

**Why:** Cleaner syntax, better expressiveness, fewer lines of code, performance improvements, optimized standard library features, and avoids learning outdated patterns.

---

## python/strict-typing-enforcement

Never use `Any` or `object` in types. Always model explicit schema types.

```python
# ✓ Good: Explicit types
from pydantic import BaseModel, Field

class TranslationRequest(BaseModel):
    source_text: str
    target_language: str
    model: str = Field(..., description="Model identifier for translation")

def translate(request: TranslationRequest) -> TranslationResult:
    """Translate with explicit types - ty will catch errors."""
    ...

# ✗ Bad: Any or object
from typing import Any

def translate(request: Any) -> Any:
    """Translate with Any - no type safety."""
    ...
```

**Type configuration:**
- `ty` must be configured in **strict mode**
- Type checking must pass with zero errors before merging
- All schemas, agents, tools, and APIs use explicit types

**Pydantic fields:**
- Every Pydantic field must use `Field(..., description="...")` with a clear description
- Use built-in validators (`min_length`, `max_length`, `pattern`, `gt`, `ge`, `lt`, `le`, etc.) for validation
- Never use raw type annotation without Field for schema fields

```python
# ✓ Good: Field with description and validators
from pydantic import BaseModel, Field

class TranslationRequest(BaseModel):
    source_text: str = Field(..., min_length=1, description="Text to translate")
    target_language: str = Field(..., pattern=r'^[a-z]{2}$', description="ISO 639-1 language code")
    model: str = Field(..., description="Model identifier for translation")

# ✗ Bad: Raw type annotation without Field
from pydantic import BaseModel

class TranslationRequest(BaseModel):
    source_text: str  # No description, no validators
    target_language: str
    model: str
```

**Exceptions (extremely rare, high bar):**
`Any` or `object` only when **all** are true:
1. Fully external library/API
2. Creating types isn't practical
3. No better alternative library or API exists
4. We actually need to feature and cannot avoid it

**Never** use `Any` for internal code, schema definitions, or where types are available.

**Why:** Catches type errors at dev time instead of runtime, makes code more readable and self-documenting, and prevents whole classes of bugs before they happen.

---

## python/pydantic-only-schemas

Never use dataclasses or plain classes for schemas. All schemas must use Pydantic.

```python
# ✓ Good: Pydantic schema
from pydantic import BaseModel, Field

class TranslationRequest(BaseModel):
    source_text: str = Field(..., min_length=1, description="Text to translate")
    target_language: str = Field(..., pattern=r'^[a-z]{2}$', description="ISO 639-1 language code")

# ✗ Bad: dataclass
from dataclasses import dataclass

@dataclass
class TranslationRequest:
    source_text: str  # No validation, no serialization
    target_language: str

# ✗ Bad: Plain class
class TranslationRequest:
    def __init__(self, source_text: str, target_language: str):
        self.source_text = source_text
        self.target_language = target_language
```

**When to use Pydantic schemas:**
- API request/response models
- Configuration models
- Agent input/output schemas
- Storage document models
- Any data that crosses package boundaries

**Pydantic requirements:**
- All fields use `Field(..., description="...")` with clear description
- Use built-in validators for validation (min_length, max_length, pattern, etc.)
- Inherit from `BaseModel` or appropriate Pydantic base
- Type-safe with full type annotations

**Never use dataclasses or plain classes for:**
- Schemas that serialize/deserialize
- Data that requires validation
- Configuration models
- API contracts

**Why:** Pydantic provides automatic validation, native JSON serialization/deserialization, better type inference and IDE support than dataclasses, and catches schema errors early.

---

## architecture/naming-conventions

Use consistent naming conventions across all code. Never mix styles.

```python
# ✓ Good: Consistent snake_case for modules/functions/variables
from translation_engine import translate_scene
from config_loader import load_config

def process_scene(scene: Scene) -> TranslationResult:
    """Process single scene."""
    result = translate_scene(scene)
    return result

# ✓ Good: PascalCase for classes/types
class TranslationRequest(BaseModel):
    """Translation request model."""

class VectorStoreProtocol(Protocol):
    """Vector store interface protocol."""

class SQLiteIndex:
    """SQLite run metadata index."""

# ✗ Bad: Inconsistent naming
from TranslationEngine import translate_Scene  # PascalCase for module
from config_loader import LoadConfig  # PascalCase for function

def ProcessScene(scene: Scene) -> TranslationResult:  # PascalCase for function
    ...

class translationRequest:  # snake_case for class
    pass
```

**Python code naming:**
- Modules/files: `snake_case.py`
- Functions/variables: `snake_case`
- Classes/types: `PascalCase`

**Database naming:**
- Tables/collections: `snake_case`
- Columns/fields: `snake_case`
- Foreign keys: `{entity}_id` (e.g., `run_id`, `scene_id`)

**API naming:**
- CLI commands: `kebab-case` (e.g., `run-pipeline`, `show-status`)
- CLI options: `--snake-case` (e.g., `--run-id`, `--config-file`)

**JSON/JSONL naming:**
- Fields: `snake_case` (e.g., `run_id`, `phase_name`, `error_message`)

**Event naming:**
- Event names: `snake_case` (e.g., `run_started`, `phase_completed`, `translation_finished`)

**Why:** Consistency makes code predictable and easier to navigate; reduces confusion when multiple developers/agents work together.
