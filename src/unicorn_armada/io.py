from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Dataset
from .utils import Pair, normalize_id, pair_key


class InputError(ValueError):
    pass


def load_dataset(path: Path) -> Dataset:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise InputError(f"Dataset not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Dataset JSON is invalid: {path}") from exc
    return Dataset.model_validate(data)


def load_units_json(path: Path) -> list[int]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise InputError(f"Units file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Units JSON is invalid: {path}") from exc
    if not isinstance(data, list) or not all(isinstance(item, int) for item in data):
        raise InputError("Units JSON must be a list of integers")
    return data


def parse_units_arg(value: str) -> list[int]:
    units = []
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            units.append(int(raw))
        except ValueError as exc:
            raise InputError(f"Invalid unit size: {raw}") from exc
    if not units:
        raise InputError("Units list cannot be empty")
    return units


def load_roster_csv(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except FileNotFoundError as exc:
        raise InputError(f"Roster file not found: {path}") from exc
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return []

    header = [cell.strip().lower() for cell in rows[0]]
    start_idx = 0
    if header and header[0] == "id":
        start_idx = 1

    roster = []
    for row in rows[start_idx:]:
        if not row:
            continue
        value = normalize_id(row[0])
        if value:
            roster.append(value)
    return roster


def load_pairs_csv(path: Path) -> set[Pair]:
    try:
        text = path.read_text()
    except FileNotFoundError as exc:
        raise InputError(f"Pairs file not found: {path}") from exc

    pairs: set[Pair] = set()
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return pairs

    header = [cell.strip().lower() for cell in rows[0]]
    start_idx = 0
    if len(header) >= 2 and (header[0], header[1]) in {("a", "b"), ("left", "right")}:
        start_idx = 1

    for row in rows[start_idx:]:
        if len(row) < 2:
            continue
        left = normalize_id(row[0])
        right = normalize_id(row[1])
        if not left or not right:
            continue
        pairs.add(pair_key(left, right))
    return pairs
