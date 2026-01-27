from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .combat import compute_combat_summary
from .solver import (
    SolveError,
    build_cluster_metrics,
    build_clusters,
    build_dummy_ids,
    build_unit_members_from_clusters,
    choose_clusters_to_drop,
)

if TYPE_CHECKING:
    import random

    from .models import ClassDefinition, CombatScoringConfig
    from .utils import Pair


class BenchmarkStats(BaseModel):
    """Statistics for benchmark results."""

    count: int = Field(..., description="Number of samples in the benchmark")
    minimum: float = Field(..., description="Minimum score observed")
    maximum: float = Field(..., description="Maximum score observed")
    mean: float = Field(..., description="Mean score across all samples")
    median: float = Field(..., description="Median (p50) score")
    p75: float = Field(..., description="75th percentile score")
    p90: float = Field(..., description="90th percentile score")
    std: float = Field(..., description="Standard deviation of scores")


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    if percent <= 0:
        return values[0]
    if percent >= 1:
        return values[-1]
    position = (len(values) - 1) * percent
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[int(position)]
    weight = position - lower
    return values[lower] + (values[upper] - values[lower]) * weight


def compute_stats(values: list[float]) -> BenchmarkStats:
    if not values:
        return BenchmarkStats(
            count=0,
            minimum=0.0,
            maximum=0.0,
            mean=0.0,
            median=0.0,
            p75=0.0,
            p90=0.0,
            std=0.0,
        )

    values_sorted = sorted(values)
    count = len(values_sorted)
    total = sum(values_sorted)
    mean = total / count
    variance = sum((value - mean) ** 2 for value in values_sorted) / count
    std = math.sqrt(variance)

    return BenchmarkStats(
        count=count,
        minimum=values_sorted[0],
        maximum=values_sorted[-1],
        mean=mean,
        median=percentile(values_sorted, 0.5),
        p75=percentile(values_sorted, 0.75),
        p90=percentile(values_sorted, 0.9),
        std=std,
    )


def sample_unit_scores(
    roster: list[str],
    unit_size: int,
    samples: int,
    rng: random.Random,
    character_classes: dict[str, str],
    classes: list[ClassDefinition],
    scoring: CombatScoringConfig,
) -> list[float]:
    if unit_size <= 0 or unit_size > len(roster) or samples <= 0:
        return []

    scores: list[float] = []
    for _ in range(samples):
        unit = rng.sample(roster, unit_size)
        score = compute_combat_summary(
            [unit],
            character_classes,
            classes,
            scoring,
        ).total_score
        scores.append(score)
    return scores


def generate_random_assignment(
    roster: list[str],
    units: list[int],
    rapport_edges: set[Pair],
    whitelist: set[Pair],
    blacklist: set[Pair],
    rng: random.Random,
    *,
    max_attempts: int = 50,
) -> list[list[str]] | None:
    if not units:
        raise SolveError("At least one unit size is required")
    if any(size < 2 for size in units):
        raise SolveError("Unit sizes must be at least 2")
    total_slots = sum(units)
    if total_slots <= 0:
        raise SolveError("Unit sizes must sum to a positive total")

    roster_set = set(roster)
    if len(roster) != len(roster_set):
        raise SolveError("Roster contains duplicate character ids")

    if whitelist & blacklist:
        raise SolveError("Whitelist and blacklist overlap")

    for pair in whitelist:
        if not pair.issubset(roster_set):
            raise SolveError("Whitelist pair contains ids missing from roster")
        if pair not in rapport_edges:
            raise SolveError("Whitelist pair is not a valid rapport")

    dummy_ids = build_dummy_ids(roster_set, total_slots - len(roster))
    if dummy_ids:
        roster = roster + sorted(dummy_ids)
        roster_set |= dummy_ids

    clusters = build_clusters(roster, whitelist, blacklist, max(units))

    extra = sum(cluster.size for cluster in clusters) - total_slots
    if extra < 0:
        raise SolveError("Not enough characters to fill all units")

    if extra > 0:
        drop_indices = choose_clusters_to_drop(clusters, rapport_edges, extra)
        clusters = [
            cluster for idx, cluster in enumerate(clusters) if idx not in drop_indices
        ]

    assigned_set = {member for cluster in clusters for member in cluster.members}
    blacklist = {pair for pair in blacklist if pair.issubset(assigned_set)}

    _, cluster_conflicts = build_cluster_metrics(clusters, set(), blacklist)

    for _ in range(max_attempts):
        unit_clusters = _assign_clusters_randomly(
            clusters, units, cluster_conflicts, rng
        )
        if unit_clusters is None:
            continue
        return build_unit_members_from_clusters(unit_clusters, clusters, dummy_ids)

    return None


def _assign_clusters_randomly(
    clusters,
    units: list[int],
    cluster_conflicts: list[list[bool]],
    rng: random.Random,
) -> list[list[int]] | None:
    capacities = list(units)
    assignments: list[list[int]] = [[] for _ in units]

    order = sorted(
        range(len(clusters)),
        key=lambda idx: (clusters[idx].size, rng.random()),
        reverse=True,
    )

    for cluster_idx in order:
        size = clusters[cluster_idx].size
        best_remaining = None
        candidates: list[int] = []
        for unit_idx, capacity in enumerate(capacities):
            if capacity < size:
                continue
            if any(
                cluster_conflicts[cluster_idx][other] for other in assignments[unit_idx]
            ):
                continue
            remaining = capacity - size
            if best_remaining is None or remaining < best_remaining:
                best_remaining = remaining
                candidates = [unit_idx]
            elif remaining == best_remaining:
                candidates.append(unit_idx)
        if not candidates:
            return None
        chosen = rng.choice(candidates)
        assignments[chosen].append(cluster_idx)
        capacities[chosen] -= size

    if any(capacity != 0 for capacity in capacities):
        return None
    return assignments
