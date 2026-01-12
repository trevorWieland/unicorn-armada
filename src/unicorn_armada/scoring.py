from __future__ import annotations

from .utils import Pair, pair_key


def bond_pairs_in_unit(unit: list[str], bond_edges: set[Pair]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for i in range(len(unit)):
        for j in range(i + 1, len(unit)):
            if pair_key(unit[i], unit[j]) in bond_edges:
                pairs.append((unit[i], unit[j]))
    return pairs


def score_unit(unit: list[str], bond_edges: set[Pair]) -> int:
    return len(bond_pairs_in_unit(unit, bond_edges))
