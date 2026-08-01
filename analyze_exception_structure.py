#!/usr/bin/env python3
"""
Structural audit of the exceptional graph GCZTfO.

The program verifies:
- its proposed construction;
- degrees, triangles, maximal cliques, and bridges;
- its full automorphism group and vertex orbits;
- an inclusion-exclusion derivation of D_t(G,x).
"""

from __future__ import annotations

import itertools
import math
import sys
from collections import defaultdict

from validate_graph6_census import decode_graph6


GRAPH6 = "GCZTfO"
EXPECTED_COEFFICIENTS = [0, 0, 1, 6, 40, 50, 28, 8, 1]


def edge_set(graph) -> set[tuple[int, int]]:
    return {
        (min(u, v), max(u, v))
        for u, v in graph.edges
    }


def adjacency_sets(graph) -> tuple[frozenset[int], ...]:
    adjacency = [set() for _ in range(graph.order)]

    for u, v in graph.edges:
        adjacency[u].add(v)
        adjacency[v].add(u)

    return tuple(frozenset(neighbors) for neighbors in adjacency)


def induced_edges(
    edges: set[tuple[int, int]],
    vertices: set[int],
) -> set[tuple[int, int]]:
    return {
        edge
        for edge in edges
        if edge[0] in vertices and edge[1] in vertices
    }


def all_edges_on(vertices: set[int]) -> set[tuple[int, int]]:
    return {
        (min(u, v), max(u, v))
        for u, v in itertools.combinations(sorted(vertices), 2)
    }


def verify_construction(graph) -> None:
    """
    Verify that GCZTfO consists of two diamonds K4-e joined by
    a matching of size three.
    """
    edges = edge_set(graph)

    left = {0, 3, 5, 6}
    right = {1, 2, 4, 7}

    expected_left = all_edges_on(left) - {(5, 6)}
    expected_right = all_edges_on(right) - {(1, 2)}
    expected_cross = {(0, 7), (1, 5), (2, 6)}

    actual_left = induced_edges(edges, left)
    actual_right = induced_edges(edges, right)
    actual_cross = edges - actual_left - actual_right

    if actual_left != expected_left:
        raise AssertionError(
            f"Left diamond mismatch: expected {sorted(expected_left)}, "
            f"obtained {sorted(actual_left)}."
        )

    if actual_right != expected_right:
        raise AssertionError(
            f"Right diamond mismatch: expected {sorted(expected_right)}, "
            f"obtained {sorted(actual_right)}."
        )

    if actual_cross != expected_cross:
        raise AssertionError(
            f"Cross-edge mismatch: expected {sorted(expected_cross)}, "
            f"obtained {sorted(actual_cross)}."
        )

    print("Construction verified:")
    print(f"  Left copy of K4-e:  vertices {sorted(left)}")
    print(f"  Missing left edge:  (5, 6)")
    print(f"  Right copy of K4-e: vertices {sorted(right)}")
    print(f"  Missing right edge: (1, 2)")
    print(f"  Joining matching:   {sorted(expected_cross)}")


def triangles(graph) -> list[tuple[int, int, int]]:
    adjacency = adjacency_sets(graph)
    result = []

    for triple in itertools.combinations(range(graph.order), 3):
        if all(
            v in adjacency[u]
            for u, v in itertools.combinations(triple, 2)
        ):
            result.append(triple)

    return result


def maximal_cliques(graph) -> list[tuple[int, ...]]:
    adjacency = adjacency_sets(graph)
    cliques: list[frozenset[int]] = []

    for size in range(1, graph.order + 1):
        for candidate in itertools.combinations(range(graph.order), size):
            candidate_set = frozenset(candidate)

            if all(
                v in adjacency[u]
                for u, v in itertools.combinations(candidate, 2)
            ):
                cliques.append(candidate_set)

    maximal = [
        clique
        for clique in cliques
        if not any(clique < other for other in cliques)
    ]

    return sorted(
        (tuple(sorted(clique)) for clique in maximal),
        key=lambda clique: (-len(clique), clique),
    )


def component_count(
    order: int,
    edges: set[tuple[int, int]],
) -> int:
    adjacency = [set() for _ in range(order)]

    for u, v in edges:
        adjacency[u].add(v)
        adjacency[v].add(u)

    unseen = set(range(order))
    count = 0

    while unseen:
        count += 1
        start = min(unseen)
        unseen.remove(start)
        stack = [start]

        while stack:
            vertex = stack.pop()

            for neighbor in adjacency[vertex]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)

    return count


def bridges(graph) -> list[tuple[int, int]]:
    edges = edge_set(graph)
    original_components = component_count(graph.order, edges)
    result = []

    for edge in sorted(edges):
        remaining = edges - {edge}

        if component_count(graph.order, remaining) > original_components:
            result.append(edge)

    return result


def is_automorphism(
    permutation: tuple[int, ...],
    graph_edges: set[tuple[int, int]],
    order: int,
) -> bool:
    for u in range(order):
        for v in range(u + 1, order):
            original_edge = (u, v) in graph_edges

            image = tuple(
                sorted((permutation[u], permutation[v]))
            )
            image_edge = image in graph_edges

            if original_edge != image_edge:
                return False

    return True


def automorphism_group(graph) -> list[tuple[int, ...]]:
    edges = edge_set(graph)

    return [
        permutation
        for permutation in itertools.permutations(range(graph.order))
        if is_automorphism(permutation, edges, graph.order)
    ]


def automorphism_orbits(
    order: int,
    automorphisms: list[tuple[int, ...]],
) -> list[list[int]]:
    unseen = set(range(order))
    orbits = []

    while unseen:
        representative = min(unseen)
        orbit = {
            permutation[representative]
            for permutation in automorphisms
        }

        orbits.append(sorted(orbit))
        unseen -= orbit

    return sorted(orbits, key=lambda orbit: (orbit[0], len(orbit)))


def inclusion_exclusion_certificate(graph):
    """
    A subset S fails total domination iff S is contained in

        F_v = V \\ N(v)

    for at least one vertex v.

    Inclusion-exclusion gives

        B_G(x)
        = sum_{empty != I subseteq V}
          (-1)^(|I|+1) (1+x)^|intersection_{v in I} F_v|,

    where B_G counts the non-total-dominating subsets.

    Terms are aggregated by intersection cardinality.
    """
    vertices = set(range(graph.order))
    adjacency = adjacency_sets(graph)

    forbidden_sets = [
        vertices - set(adjacency[vertex])
        for vertex in range(graph.order)
    ]

    aggregate: defaultdict[int, int] = defaultdict(int)

    for witness_mask in range(1, 1 << graph.order):
        intersection = set(vertices)
        witness_count = 0

        for vertex in range(graph.order):
            if (witness_mask >> vertex) & 1:
                intersection &= forbidden_sets[vertex]
                witness_count += 1

        sign = 1 if witness_count % 2 == 1 else -1
        aggregate[len(intersection)] += sign

    aggregate = defaultdict(
        int,
        {
            size: coefficient
            for size, coefficient in aggregate.items()
            if coefficient != 0
        },
    )

    bad_coefficients = []

    for subset_size in range(graph.order + 1):
        count = sum(
            multiplier * math.comb(intersection_size, subset_size)
            for intersection_size, multiplier in aggregate.items()
            if intersection_size >= subset_size
        )
        bad_coefficients.append(count)

    total_coefficients = [
        math.comb(graph.order, subset_size) - bad_coefficients[subset_size]
        for subset_size in range(graph.order + 1)
    ]

    return forbidden_sets, dict(sorted(aggregate.items())), (
        bad_coefficients
    ), total_coefficients


def linear_combination_string(aggregate: dict[int, int]) -> str:
    terms = []

    for exponent in sorted(aggregate, reverse=True):
        coefficient = aggregate[exponent]

        if coefficient == 1:
            term = f"(1+x)^{exponent}"
        elif coefficient == -1:
            term = f"-(1+x)^{exponent}"
        elif coefficient > 0:
            term = f"{coefficient}(1+x)^{exponent}"
        else:
            term = f"-{abs(coefficient)}(1+x)^{exponent}"

        terms.append(term)

    expression = " + ".join(terms)
    return expression.replace("+ -", "- ")


def main() -> int:
    try:
        graph = decode_graph6(GRAPH6)

        print(f"Structural analysis of graph6 {GRAPH6}")
        print("=" * 80)
        print(f"Order: {graph.order}")
        print(f"Edges: {sorted(edge_set(graph))}")
        print()

        verify_construction(graph)

        adjacency = adjacency_sets(graph)
        degrees = [
            len(adjacency[vertex])
            for vertex in range(graph.order)
        ]

        print()
        print(f"Degrees by vertex: {degrees}")
        print(f"Degree sequence:   {sorted(degrees, reverse=True)}")
        print(f"Triangles:         {triangles(graph)}")
        print(f"Maximal cliques:   {maximal_cliques(graph)}")
        print(f"Bridges:           {bridges(graph)}")

        print()
        print("Calculating full automorphism group...")
        automorphisms = automorphism_group(graph)
        orbits = automorphism_orbits(graph.order, automorphisms)

        print(f"Automorphism-group order: {len(automorphisms)}")
        print(f"Vertex orbits:            {orbits}")

        (
            forbidden_sets,
            aggregate,
            bad_coefficients,
            total_coefficients,
        ) = inclusion_exclusion_certificate(graph)

        print()
        print("Forbidden sets F_v = V \\ N(v)")
        print("=" * 80)

        for vertex, forbidden in enumerate(forbidden_sets):
            print(f"F_{vertex} = {sorted(forbidden)}")

        print()
        print("Aggregated inclusion-exclusion multipliers")
        print("=" * 80)

        for intersection_size, multiplier in aggregate.items():
            print(
                f"Intersection size {intersection_size}: "
                f"multiplier {multiplier}"
            )

        bad_expression = linear_combination_string(aggregate)

        print()
        print("Non-total-dominating-set polynomial:")
        print(f"B_G(x) = {bad_expression}")
        print(f"Expanded coefficients: {bad_coefficients}")

        print()
        print("Since D_t(G,x) = (1+x)^8 - B_G(x):")
        print(f"Total-domination coefficients: {total_coefficients}")

        if total_coefficients != EXPECTED_COEFFICIENTS:
            raise AssertionError(
                f"Expected {EXPECTED_COEFFICIENTS}, "
                f"obtained {total_coefficients}."
            )

        print()
        print("ANALYTICAL COEFFICIENT CHECK PASSED")
        print(
            "The inclusion-exclusion derivation exactly reproduces "
            "the independently verified polynomial."
        )

        return 0

    except (AssertionError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())