from __future__ import annotations

from typing import Iterable


Pair = frozenset[str]


def normalize_id(value: str) -> str:
    return value.strip()


def pair_key(a: str, b: str) -> Pair:
    if a == b:
        raise ValueError("Pair cannot contain identical ids")
    return frozenset((a, b))


def normalize_ids(values: Iterable[str]) -> list[str]:
    return [normalize_id(value) for value in values if value.strip()]
