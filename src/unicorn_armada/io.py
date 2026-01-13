from __future__ import annotations

import csv
import json
from pathlib import Path

from pydantic import ValidationError

from .models import CombatScoringConfig, Dataset
from .utils import Pair, normalize_id, normalize_tag, pair_key


class InputError(ValueError):
    pass


def load_dataset(path: Path) -> Dataset:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise InputError(f"Dataset not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Dataset JSON is invalid: {path}") from exc
    try:
        return Dataset.model_validate(data)
    except ValidationError as exc:
        raise InputError(f"Dataset JSON failed validation: {path}") from exc


def load_combat_scoring_json(path: Path) -> CombatScoringConfig:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise InputError(f"Combat scoring file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Combat scoring JSON is invalid: {path}") from exc
    return CombatScoringConfig.model_validate(data)


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


def load_character_classes_csv(path: Path) -> dict[str, str]:
    try:
        text = path.read_text()
    except FileNotFoundError as exc:
        raise InputError(f"Character classes file not found: {path}") from exc

    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return {}

    header = [cell.strip().lower() for cell in rows[0]]
    start_idx = 0
    if (
        len(header) >= 2
        and header[0] in {"id", "character"}
        and header[1]
        in {
            "class",
            "class_id",
        }
    ):
        start_idx = 1

    mapping: dict[str, str] = {}
    for row in rows[start_idx:]:
        if len(row) < 2:
            continue
        character_id = normalize_id(row[0])
        class_id = normalize_tag(row[1])
        if not character_id or not class_id:
            continue
        existing = mapping.get(character_id)
        if existing is not None and existing != class_id:
            raise InputError(
                f"Character classes contain conflicting entries for {character_id}"
            )
        mapping[character_id] = class_id
    return mapping


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
