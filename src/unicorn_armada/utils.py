from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

Pair = frozenset[str]


def normalize_id(value: str) -> str:
    return value.strip()


def normalize_tag(value: str) -> str:
    return value.strip().lower()


def pair_key(a: str, b: str) -> Pair:
    if a == b:
        raise ValueError("Pair cannot contain identical ids")
    return frozenset((a, b))


def normalize_ids(values: Iterable[str]) -> list[str]:
    return [normalize_id(value) for value in values if value.strip()]
