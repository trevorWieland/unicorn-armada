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
- `out/solution.json`
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

### Minimum combat score

Use `--min-combat-score` to require a minimum total combat score for a solution:

```bash
uv run unicorn-rapport solve-units \
  --units 4,3,4,3,4,3 \
  --min-combat-score 6
```

### Benchmarking combat scores

Use `benchmark-units` to estimate what a "good" combat score looks like for your
roster and unit sizes. It samples random valid assignments and random units of
sizes 2-6 to produce percentile-based recommendations.

```bash
uv run unicorn-rapport benchmark-units \
  --units 4,3,4,3,4,3
```

Outputs:
- `out/benchmark.json`
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

`out/solution.json` includes a `combat` object:

- `unit_scores`: combat score per unit
- `unit_breakdowns`: per-unit role/capability counts and unknown members
- `total_score`: sum of unit scores
