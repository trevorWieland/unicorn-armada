# Unicorn Armada Rapport Planner

A small CLI for packing Unicorn Overlord characters into units to maximize rapport pairs, while enforcing required/forbidden pairings.

## Quick start

```bash
uv run unicorn-rapport solve-units \
  --units 4,3,4,3,4,3
```

Defaults:
- `data/dataset.json`
- `config/roster.csv` (if missing, all dataset characters are used)
- `config/whitelist.csv` (optional)
- `config/blacklist.csv` (optional)
- `config/character_classes.csv` (optional, combat metadata)
- `config/combat_scoring.json` (optional, combat metadata)

Outputs:
- `out/solution.json` (API response envelope)
- `out/summary.txt`

## Input formats

### Dataset JSON

```json
{
  "characters": [
    {"id": "alain", "name": "Alain"},
    {"id": "scarlett", "name": "Scarlett"}
  ],
  "classes": [
    {
      "id": "lord",
      "name": "Lord",
      "roles": ["frontline"],
      "capabilities": [],
      "row_preference": "front",
      "class_types": ["sword", "shield", "infantry"],
      "unit_type": "infantry",
      "assist_type": "none",
      "leader_effect": {
        "name": "Morale Boost",
        "description": "Gain more Valor Points when defeating enemy units."
      },
      "class_trait": null,
      "stamina": 6,
      "mobility": 100,
      "promotes_to": "high_lord"
    }
  ],
  "class_lines": [
    {"id": "lord", "classes": ["lord"]}
  ],
  "character_classes": {
    "alain": {"default_class": "lord", "class_line": "lord"}
  },
  "rapports": [
    {"id": "alain", "pairs": ["scarlett"]},
    {"id": "scarlett", "pairs": ["alain"]}
  ]
}
```

Notes:
- Duplicate or mirrored pairs are automatically deduped.
- You can omit an id from `rapports` to imply no listed pairs, or include an empty list.
 - If the roster is smaller than the total slots, units will contain empty slots.

### Roster CSV

```csv
id
alain
scarlet
```

If omitted, all characters in the dataset are considered available.

### Whitelist / Blacklist CSV

```csv
a,b
alain,scarlet
```

- Whitelist pairs must be valid rapports and must appear together.
- Blacklist pairs must not appear together.

### Unit sizes

Pass a comma-separated list:

```bash
--units 4,3,4,3,4,3
```

Or provide a JSON list:

```json
[4,3,4,3,4,3]
```

## Notes

- Units are always fully filled.
- If roster size exceeds total slots, the solver drops the least promising whitelist-compatible clusters.
- Results are deterministic for the same seed.
- When class metadata is available, combat score is used as a tie-breaker after rapport.
- CLI emits structured JSONL logs to stderr (e.g., `2> logs.jsonl`).

## Combat metadata (optional)

The CLI can compute a per-unit combat score based on class roles and capability tags.
This is reported in `out/solution.json` and used as a tie-breaker after rapport.
If class data is missing, combat scores default to 0.

### Character Classes CSV

`config/character_classes.csv`:

```csv
id,class
alain,lord
scarlett,priestess
```

Overrides the dataset default class for a character. Overrides must be valid for
that character's class line in `data/dataset.json`.

**Important:** All characters in your roster must have class data. Characters without a class mapping or with unknown class IDs will cause the solver to fail with an error. Ensure `data/dataset.json` contains complete class definitions for all characters in your roster.

### Minimum combat score

Use `--min-combat-score` to require a minimum total combat score for a solution:

```bash
uv run unicorn-rapport solve-units \
  --units 4,3,4,3,4,3 \
  --min-combat-score 6
```

### Detailed combat summary

Use `--combat-summary` to enable detailed combat breakdowns in the summary output:

```bash
uv run unicorn-rapport solve-units \
  --units 4,3,4,3,4,3 \
  --combat-summary
```

When enabled, `out/summary.txt` will include a detailed breakdown section:

```
Total rapports: 54
Total combat score: 34.50
Unit 1 (5 slots): 7 rapports, 3.50 combat
berenice, mordon, adel, clive, rolf
...

## Combat Summary Breakdown

Unit 1 (3.50 combat):
  Roles: frontline, support
  Capabilities: archer, cavalry

Unit 2 (2.00 combat):
  Roles: backline, support
  Capabilities: caster, assist
```

The breakdown shows:
- Combat score per unit
- Roles present (e.g., frontline, support, backline)
- Capabilities present (e.g., archer, caster, assist)

### Benchmarking combat scores

Use `benchmark-units` to estimate what a "good" combat score looks like for your
roster and unit sizes. It samples random valid assignments and random units of
sizes 2-6 to produce percentile-based recommendations.

```bash
uv run unicorn-rapport benchmark-units \
  --units 4,3,4,3,4,3
```

Outputs:
- `out/benchmark.json` (API response envelope)
- `out/benchmark.txt`

### Combat Scoring JSON

`config/combat_scoring.json`:

```json
{
  "role_weights": {
    "frontline": 1.0,
    "backline": 1.0,
    "support": 1.0
  },
  "capability_weights": {
    "assist": 0.5,
    "cavalry": 0.5,
    "flying": 0.5,
    "archer": 0.5,
    "caster": 0.5
  }
}
```

### Combat output

`out/solution.json` uses the API response envelope; the solution lives under `data`.

```json
{
  "data": {
    "units": [],
    "unit_rapports": [],
    "total_rapports": 0,
    "unassigned": [],
    "seed": 0,
    "restarts": 50,
    "swap_iterations": 200,
    "combat": {
      "unit_scores": [],
      "unit_breakdowns": [],
      "total_score": 0,
      "coverage": {},
      "diversity": {}
    }
  },
  "error": null,
  "meta": {
    "timestamp": "2026-01-27T00:00:00Z"
  }
}
```

The `combat` object contains:

- `unit_scores`: combat score per unit
- `unit_breakdowns`: per-unit role/capability counts and unknown members
- `total_score`: sum of unit scores
- `coverage`: army-level coverage breakdown (assist types, unit types)
- `diversity`: leader diversity breakdown (leaders, unique count, score)
- `army_total_score`: total score including unit + coverage + diversity

## Syncing rapports

Use `sync-rapports` to normalize rapport pairs in the dataset file.

Outputs:
- Dataset JSON at `--out` (raw dataset format)
- `out/sync-rapports.json` report (API response envelope)

The report payload includes `changed`, `output_path`, and `stats` (added pairs,
duplicates, skipped entries).

## Army Coverage & Diversity (Phase 2)

The solver now includes army-level strategic scoring alongside unit-level combat scoring.

### Coverage Scoring

Encourages diverse assist types and unit types across your army.

- Assist types: ranged, magick, healing
- Unit types: infantry, cavalry, flying

Coverage is scored by giving a bonus for each unique type present. Soft scoring means more variety always helps.

### Leader Diversity

Encourages diverse leader classes across units. Each unit gets a leader (first character with leader effect, then first with valid class data), and unique leader classes earn bonuses.

### Using Presets

Quick configurations for common playstyles:

```bash
# Balanced: good mix of offense and support
uv run unicorn-rapport solve-units --units 4,3,4,3,4,3 --preset balanced

# Offensive: prioritize ranged attacks and mobility
uv run unicorn-rapport solve-units --units 4,3,4,3,4,3 --preset offensive

# Defensive: prioritize healing and sturdy units
uv run unicorn-rapport solve-units --units 4,3,4,3,4,3 --preset defensive

# Magic-heavy: prioritize spellcasters
uv run unicorn-rapport solve-units --units 4,3,4,3,4,3 --preset magic-heavy
```

### Customizing Weights

Edit `config/combat_scoring.json` to fine-tune:

```json
{
  "coverage": {
    "enabled": true,
    "assist_type_weights": {
      "ranged": 0.7,  // Increase ranged importance
      "magick": 0.5,
      "healing": 0.3   // Decrease healing importance
    },
    "unit_type_weights": {
      "infantry": 0.3,
      "cavalry": 0.3,
      "flying": 0.3
    },
    "target_multiplier": 1.0  // 1.0 = soft, 0.0 = hard cap
  },
  "diversity": {
    "enabled": true,
    "unique_leader_bonus": 1.5,    // Reward unique leaders more
    "duplicate_leader_penalty": 0.3, // Penalize duplicates less
    "mode": "class"               // How to identify unique leaders
  }
}
```

### CLI Flags

Override config settings with CLI flags:

```bash
# Disable coverage temporarily
uv run unicorn-rapport solve-units --units 4,3,4,3,4,3 --disable-coverage

# Change diversity mode
uv run unicorn-rapport solve-units --units 4,3,4,3,4,3 --diversity-mode unit_type
```
