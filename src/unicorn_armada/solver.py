from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import random

from .models import Solution
from .scoring import score_unit
from .utils import Pair


class SolveError(ValueError):
    pass


@dataclass(frozen=True)
class Cluster:
    members: tuple[str, ...]

    @property
    def size(self) -> int:
        return len(self.members)


@dataclass
class UnitState:
    capacity: int
    clusters: list[int]


class UnionFind:
    def __init__(self, items: Iterable[str]) -> None:
        self._parent = {item: item for item in items}
        self._rank = {item: 0 for item in items}

    def find(self, item: str) -> str:
        parent = self._parent[item]
        if parent != item:
            self._parent[item] = self.find(parent)
        return self._parent[item]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self._rank[root_left] < self._rank[root_right]:
            self._parent[root_left] = root_right
        elif self._rank[root_left] > self._rank[root_right]:
            self._parent[root_right] = root_left
        else:
            self._parent[root_right] = root_left
            self._rank[root_left] += 1


def solve(
    roster: list[str],
    units: list[int],
    bond_edges: set[Pair],
    whitelist: set[Pair],
    blacklist: set[Pair],
    *,
    seed: int,
    restarts: int,
    swap_iterations: int,
) -> Solution:
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
        if pair not in bond_edges:
            raise SolveError("Whitelist pair is not a valid bond")

    dummy_ids = build_dummy_ids(roster_set, total_slots - len(roster))
    if dummy_ids:
        roster = roster + sorted(dummy_ids)
        roster_set |= dummy_ids

    clusters = build_clusters(roster, whitelist, blacklist, max(units))

    extra = sum(cluster.size for cluster in clusters) - total_slots
    if extra < 0:
        raise SolveError("Not enough characters to fill all units")

    unassigned_members: list[str] = []
    if extra > 0:
        drop_indices = choose_clusters_to_drop(clusters, bond_edges, extra)
        kept_clusters = [
            cluster for idx, cluster in enumerate(clusters) if idx not in drop_indices
        ]
        unassigned_members = sorted(
            member
            for idx, cluster in enumerate(clusters)
            if idx in drop_indices
            for member in cluster.members
        )
        clusters = kept_clusters

    assigned_set = {member for cluster in clusters for member in cluster.members}
    bond_edges = {pair for pair in bond_edges if pair.issubset(assigned_set)}
    blacklist = {pair for pair in blacklist if pair.issubset(assigned_set)}

    cluster_bonds, cluster_conflicts = build_cluster_metrics(
        clusters, bond_edges, blacklist
    )
    potentials = compute_cluster_potentials(clusters, bond_edges)

    rng = random.Random(seed)
    best_units: list[list[int]] | None = None
    best_score = -1
    best_unit_scores: list[int] = []

    for _ in range(max(1, restarts)):
        unit_states = generate_initial_assignment(
            clusters, units, cluster_bonds, cluster_conflicts, potentials, rng
        )
        if unit_states is None:
            continue
        unit_clusters = [state.clusters for state in unit_states]
        improve_by_swaps(
            unit_clusters,
            clusters,
            cluster_bonds,
            cluster_conflicts,
            swap_iterations,
        )
        total_score, unit_scores = score_cluster_units(unit_clusters, cluster_bonds)
        if total_score > best_score:
            best_score = total_score
            best_units = [list(unit) for unit in unit_clusters]
            best_unit_scores = unit_scores

    if best_units is None:
        raise SolveError("Unable to find a valid unit assignment")

    unit_members: list[list[str]] = []
    for unit in best_units:
        members: list[str] = []
        for cluster_idx in unit:
            members.extend(clusters[cluster_idx].members)
        if dummy_ids:
            members = [member for member in members if member not in dummy_ids]
        unit_members.append(members)

    unit_bonds = [score_unit(unit, bond_edges) for unit in unit_members]
    if dummy_ids and unassigned_members:
        unassigned_members = [
            member for member in unassigned_members if member not in dummy_ids
        ]

    return Solution(
        units=unit_members,
        unit_bonds=unit_bonds,
        total_bonds=sum(unit_bonds),
        unassigned=unassigned_members,
        seed=seed,
        restarts=restarts,
        swap_iterations=swap_iterations,
    )


def build_dummy_ids(roster_set: set[str], deficit: int) -> set[str]:
    if deficit <= 0:
        return set()
    dummy_ids: set[str] = set()
    next_idx = 1
    while len(dummy_ids) < deficit:
        candidate = f"__empty_slot__{next_idx}"
        next_idx += 1
        if candidate in roster_set or candidate in dummy_ids:
            continue
        dummy_ids.add(candidate)
    return dummy_ids


def build_clusters(
    roster: list[str],
    whitelist: set[Pair],
    blacklist: set[Pair],
    max_unit_size: int,
) -> list[Cluster]:
    uf = UnionFind(roster)
    for pair in whitelist:
        left, right = tuple(pair)
        uf.union(left, right)

    root_to_members: dict[str, list[str]] = {}
    for member in roster:
        root = uf.find(member)
        root_to_members.setdefault(root, []).append(member)

    clusters = []
    for members in root_to_members.values():
        members_sorted = tuple(sorted(members))
        if len(members_sorted) > max_unit_size:
            raise SolveError(
                "Whitelist requires a group larger than the maximum unit size"
            )
        clusters.append(Cluster(members_sorted))

    clusters.sort(key=lambda cluster: cluster.members)

    member_to_cluster = {}
    for idx, cluster in enumerate(clusters):
        for member in cluster.members:
            member_to_cluster[member] = idx

    for pair in blacklist:
        left, right = tuple(pair)
        if left not in member_to_cluster or right not in member_to_cluster:
            continue
        if member_to_cluster[left] == member_to_cluster[right]:
            raise SolveError("Blacklist pair conflicts with required whitelist group")

    return clusters


def compute_cluster_potentials(
    clusters: list[Cluster], bond_edges: set[Pair]
) -> list[int]:
    cluster_index = {}
    for idx, cluster in enumerate(clusters):
        for member in cluster.members:
            cluster_index[member] = idx

    potentials = [0 for _ in clusters]
    for pair in bond_edges:
        left, right = tuple(pair)
        if left not in cluster_index or right not in cluster_index:
            continue
        left_idx = cluster_index[left]
        right_idx = cluster_index[right]
        potentials[left_idx] += 1
        if left_idx != right_idx:
            potentials[right_idx] += 1

    return potentials


def choose_clusters_to_drop(
    clusters: list[Cluster], bond_edges: set[Pair], extra: int
) -> set[int]:
    if extra <= 0:
        return set()

    potentials = compute_cluster_potentials(clusters, bond_edges)
    dp_penalty = [float("inf")] * (extra + 1)
    dp_choice: list[tuple[int, int] | None] = [None] * (extra + 1)
    dp_penalty[0] = 0.0

    for idx, cluster in enumerate(clusters):
        size = cluster.size
        penalty = potentials[idx]
        for total in range(extra, size - 1, -1):
            prev = total - size
            candidate = dp_penalty[prev] + penalty
            if candidate < dp_penalty[total]:
                dp_penalty[total] = candidate
                dp_choice[total] = (prev, idx)

    if dp_penalty[extra] == float("inf"):
        raise SolveError("Roster cannot be trimmed to fit unit slots with whitelist")

    selected: set[int] = set()
    current = extra
    while current > 0:
        choice = dp_choice[current]
        if choice is None:
            break
        prev, idx = choice
        selected.add(idx)
        current = prev

    if current != 0:
        raise SolveError("Failed to reconstruct roster trimming choices")

    return selected


def build_cluster_metrics(
    clusters: list[Cluster],
    bond_edges: set[Pair],
    blacklist: set[Pair],
) -> tuple[list[list[int]], list[list[bool]]]:
    count = len(clusters)
    cluster_index = {}
    for idx, cluster in enumerate(clusters):
        for member in cluster.members:
            cluster_index[member] = idx

    bonds = [[0 for _ in range(count)] for _ in range(count)]
    for pair in bond_edges:
        left, right = tuple(pair)
        if left not in cluster_index or right not in cluster_index:
            continue
        left_idx = cluster_index[left]
        right_idx = cluster_index[right]
        if left_idx == right_idx:
            bonds[left_idx][right_idx] += 1
        else:
            bonds[left_idx][right_idx] += 1
            bonds[right_idx][left_idx] += 1

    conflicts = [[False for _ in range(count)] for _ in range(count)]
    for pair in blacklist:
        left, right = tuple(pair)
        if left not in cluster_index or right not in cluster_index:
            continue
        left_idx = cluster_index[left]
        right_idx = cluster_index[right]
        if left_idx == right_idx:
            raise SolveError("Blacklist pair conflicts with required whitelist group")
        conflicts[left_idx][right_idx] = True
        conflicts[right_idx][left_idx] = True

    return bonds, conflicts


def generate_initial_assignment(
    clusters: list[Cluster],
    units: list[int],
    cluster_bonds: list[list[int]],
    cluster_conflicts: list[list[bool]],
    potentials: list[int],
    rng: random.Random,
) -> list[UnitState] | None:
    count = len(clusters)
    order = sorted(
        range(count),
        key=lambda idx: (clusters[idx].size, potentials[idx], rng.random()),
        reverse=True,
    )

    states = [UnitState(capacity=size, clusters=[]) for size in units]

    for cluster_idx in order:
        size = clusters[cluster_idx].size
        best_unit = None
        best_score = None
        best_remaining = None
        for unit_idx, state in enumerate(states):
            if state.capacity < size:
                continue
            if any(cluster_conflicts[cluster_idx][other] for other in state.clusters):
                continue
            increment = sum(
                cluster_bonds[cluster_idx][other] for other in state.clusters
            )
            remaining = state.capacity - size
            if (
                best_unit is None
                or increment > best_score
                or (increment == best_score and remaining < best_remaining)
            ):
                best_unit = unit_idx
                best_score = increment
                best_remaining = remaining
        if best_unit is None:
            return None
        states[best_unit].clusters.append(cluster_idx)
        states[best_unit].capacity -= size

    if any(state.capacity != 0 for state in states):
        return None

    return states


def improve_by_swaps(
    unit_clusters: list[list[int]],
    clusters: list[Cluster],
    cluster_bonds: list[list[int]],
    cluster_conflicts: list[list[bool]],
    max_iterations: int,
) -> None:
    if max_iterations <= 0:
        return

    for _ in range(max_iterations):
        improved = False
        for left_idx in range(len(unit_clusters)):
            for right_idx in range(left_idx + 1, len(unit_clusters)):
                left_unit = unit_clusters[left_idx]
                right_unit = unit_clusters[right_idx]
                for i, left_cluster in enumerate(left_unit):
                    for j, right_cluster in enumerate(right_unit):
                        if clusters[left_cluster].size != clusters[right_cluster].size:
                            continue
                        if has_conflict(
                            left_cluster,
                            right_unit,
                            cluster_conflicts,
                            exclude=right_cluster,
                        ):
                            continue
                        if has_conflict(
                            right_cluster,
                            left_unit,
                            cluster_conflicts,
                            exclude=left_cluster,
                        ):
                            continue
                        delta = swap_delta(
                            left_cluster,
                            right_cluster,
                            left_unit,
                            right_unit,
                            cluster_bonds,
                        )
                        if delta > 0:
                            left_unit[i], right_unit[j] = right_cluster, left_cluster
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break
        if not improved:
            break


def has_conflict(
    candidate: int,
    unit: list[int],
    cluster_conflicts: list[list[bool]],
    *,
    exclude: int | None = None,
) -> bool:
    return any(
        cluster_conflicts[candidate][other] for other in unit if other != exclude
    )


def swap_delta(
    left_cluster: int,
    right_cluster: int,
    left_unit: list[int],
    right_unit: list[int],
    cluster_bonds: list[list[int]],
) -> int:
    left_before = sum(
        cluster_bonds[left_cluster][other]
        for other in left_unit
        if other != left_cluster
    )
    right_before = sum(
        cluster_bonds[right_cluster][other]
        for other in right_unit
        if other != right_cluster
    )
    left_after = sum(
        cluster_bonds[left_cluster][other]
        for other in right_unit
        if other != right_cluster
    )
    right_after = sum(
        cluster_bonds[right_cluster][other]
        for other in left_unit
        if other != left_cluster
    )
    return (left_after + right_after) - (left_before + right_before)


def score_cluster_units(
    unit_clusters: list[list[int]],
    cluster_bonds: list[list[int]],
) -> tuple[int, list[int]]:
    total = 0
    unit_scores: list[int] = []
    for unit in unit_clusters:
        score = 0
        for idx, left in enumerate(unit):
            score += cluster_bonds[left][left]
            for right in unit[idx + 1 :]:
                score += cluster_bonds[left][right]
        unit_scores.append(score)
        total += score
    return total, unit_scores
