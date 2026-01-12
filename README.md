# Unicorn Armada Bond Planner

A small CLI for packing Unicorn Overlord characters into units to maximize bonded pairs, while enforcing required/forbidden pairings.

## Quick start

```bash
uv run unicorn-bonds solve-units \
  --units 4,3,4,3,4,3
```

Defaults:
- `data/dataset.json`
- `config/roster.csv` (if missing, all dataset characters are used)
- `config/whitelist.csv` (optional)
- `config/blacklist.csv` (optional)

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
  "bonds": [
    {"id": "alain", "pairs": ["scarlett"]},
    {"id": "scarlett", "pairs": ["alain"]}
  ]
}
```

Notes:
- Duplicate or mirrored pairs are automatically deduped.
- You can omit an id from `bonds` to imply no listed pairs, or include an empty list.
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

- Whitelist pairs must be valid bonds and must appear together.
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
