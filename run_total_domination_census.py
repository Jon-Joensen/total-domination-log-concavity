#!/usr/bin/env python3
"""
First exhaustive total-domination-polynomial census.

Scope:
    Every nonisomorphic finite simple graph without isolated vertices
    of orders 2 through 8 in the validated ANU graph6 census.

This program:
1. rechecks the census counts;
2. excludes graphs with isolated vertices;
3. enumerates all vertex subsets using integer bitmasks;
4. computes every total-domination coefficient;
5. checks internal zeros, log-concavity, and unimodality;
6. reports every non-log-concave graph in auditable detail.

It does not assume the previously claimed number or identity of exceptions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from validate_graph6_census import DecodedGraph, decode_graph6


DATA_DIRECTORY = Path("data") / "original"

EXPECTED_ALL = {
    2: 2,
    3: 4,
    4: 11,
    5: 34,
    6: 156,
    7: 1044,
    8: 12346,
}

# Independently reproduced during Stage 3A.
EXPECTED_NO_ISOLATES = {
    2: 1,
    3: 2,
    4: 7,
    5: 23,
    6: 122,
    7: 888,
    8: 11302,
}


def neighborhood_masks(graph: DecodedGraph) -> tuple[int, ...]:
    """
    Return the open neighbourhood of each vertex as an integer bitmask.

    Bit u is set in masks[v] exactly when u is adjacent to v.
    """
    masks = [0] * graph.order

    for u, v in graph.edges:
        masks[u] |= 1 << v
        masks[v] |= 1 << u

    return tuple(masks)


def has_isolated_vertex(masks: tuple[int, ...]) -> bool:
    return any(mask == 0 for mask in masks)


def is_total_dominating_subset(
    subset_mask: int,
    masks: tuple[int, ...],
) -> bool:
    """
    A subset S is total dominating exactly when N(v) intersects S
    for every vertex v.
    """
    return all((neighbor_mask & subset_mask) != 0 for neighbor_mask in masks)


def total_domination_coefficients(
    masks: tuple[int, ...],
) -> list[int]:
    """
    Enumerate all 2^n vertex subsets.

    coefficients[k] is the number of total dominating sets of size k.
    """
    order = len(masks)
    coefficients = [0] * (order + 1)

    for subset_mask in range(1 << order):
        if is_total_dominating_subset(subset_mask, masks):
            cardinality = subset_mask.bit_count()
            coefficients[cardinality] += 1

    return coefficients


def support(coefficients: list[int]) -> tuple[int, int] | None:
    nonzero_indices = [
        index
        for index, coefficient in enumerate(coefficients)
        if coefficient != 0
    ]

    if not nonzero_indices:
        return None

    return nonzero_indices[0], nonzero_indices[-1]


def has_internal_zeros(coefficients: list[int]) -> bool:
    coefficient_support = support(coefficients)

    if coefficient_support is None:
        return False

    first, last = coefficient_support
    return any(
        coefficients[index] == 0
        for index in range(first, last + 1)
    )


def log_concavity_failures(
    coefficients: list[int],
) -> list[dict[str, int]]:
    coefficient_support = support(coefficients)

    if coefficient_support is None:
        return []

    first, last = coefficient_support
    failures: list[dict[str, int]] = []

    for index in range(first + 1, last):
        square = coefficients[index] ** 2
        adjacent_product = (
            coefficients[index - 1] * coefficients[index + 1]
        )

        if square < adjacent_product:
            failures.append(
                {
                    "index": index,
                    "coefficient": coefficients[index],
                    "left_square": square,
                    "previous_coefficient": coefficients[index - 1],
                    "next_coefficient": coefficients[index + 1],
                    "right_product": adjacent_product,
                }
            )

    return failures


def is_unimodal(coefficients: list[int]) -> bool | None:
    coefficient_support = support(coefficients)

    if coefficient_support is None:
        return None

    first, last = coefficient_support
    values = coefficients[first : last + 1]

    for mode in range(len(values)):
        increasing_part = all(
            values[index] <= values[index + 1]
            for index in range(mode)
        )
        decreasing_part = all(
            values[index] >= values[index + 1]
            for index in range(mode, len(values) - 1)
        )

        if increasing_part and decreasing_part:
            return True

    return False


def connected_components(
    masks: tuple[int, ...],
) -> list[list[int]]:
    """Return connected components as sorted vertex lists."""
    order = len(masks)
    unseen = set(range(order))
    components: list[list[int]] = []

    while unseen:
        start = min(unseen)
        unseen.remove(start)

        component = [start]
        stack = [start]

        while stack:
            vertex = stack.pop()

            neighbors = [
                candidate
                for candidate in range(order)
                if (masks[vertex] >> candidate) & 1
            ]

            for neighbor in neighbors:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.append(neighbor)
                    stack.append(neighbor)

        components.append(sorted(component))

    return components


def degree_sequence(masks: tuple[int, ...]) -> list[int]:
    return sorted(
        (mask.bit_count() for mask in masks),
        reverse=True,
    )


def polynomial_string(coefficients: list[int]) -> str:
    terms: list[str] = []

    for exponent, coefficient in enumerate(coefficients):
        if coefficient == 0:
            continue

        if exponent == 0:
            variable = ""
        elif exponent == 1:
            variable = "x"
        else:
            variable = f"x^{exponent}"

        if coefficient == 1 and variable:
            terms.append(variable)
        else:
            terms.append(f"{coefficient}{variable}")

    return " + ".join(terms) if terms else "0"


def validate_integration_examples() -> None:
    """
    Verify that the graph6 decoder and bitmask enumerator work together.

    These expected vectors come from the independently hand-checked
    Stage 2 examples.
    """
    examples = [
        ("K2", "A_", [0, 0, 1]),
        ("K3", "Bw", [0, 0, 3, 1]),
        ("P4", "Ch", [0, 0, 1, 2, 1]),
        ("C4", "Cl", [0, 0, 4, 4, 1]),
        ("K1,3", "Cs", [0, 0, 3, 3, 1]),
        ("K2,2", "C]", [0, 0, 4, 4, 1]),
    ]

    print("Integrated graph6/bitmask validation")
    print("=" * 88)

    for name, graph6, expected in examples:
        graph = decode_graph6(graph6)
        masks = neighborhood_masks(graph)
        obtained = total_domination_coefficients(masks)

        if obtained != expected:
            raise AssertionError(
                f"{name} ({graph6}) failed: expected {expected}, "
                f"obtained {obtained}."
            )

        print(
            f"PASS  {name:<8} graph6={graph6:<4} "
            f"coefficients={obtained}"
        )

    print(
        f"ALL INTEGRATION TESTS PASSED: "
        f"{len(examples)}/{len(examples)}"
    )
    print()


def load_census(order: int) -> list[str]:
    path = DATA_DIRECTORY / f"graph{order}.g6"

    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run validate_graph6_census.py first."
        )

    try:
        text = path.read_text(encoding="ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path} is not ASCII data.") from exc

    records = [line.strip() for line in text.splitlines() if line.strip()]

    if len(records) != EXPECTED_ALL[order]:
        raise AssertionError(
            f"Order {order}: expected {EXPECTED_ALL[order]} records, "
            f"found {len(records)}."
        )

    if len(set(records)) != len(records):
        raise AssertionError(
            f"Order {order}: duplicate graph6 records detected."
        )

    return records


def make_exception_record(
    order: int,
    census_line: int,
    graph6: str,
    graph: DecodedGraph,
    masks: tuple[int, ...],
    coefficients: list[int],
    failures: list[dict[str, int]],
) -> dict[str, object]:
    components = connected_components(masks)
    coefficient_support = support(coefficients)

    if coefficient_support is None:
        raise AssertionError(
            "A graph without isolated vertices produced the zero polynomial."
        )

    return {
        "order": order,
        "census_line": census_line,
        "graph6": graph6,
        "edges": [list(edge) for edge in sorted(graph.edges)],
        "degree_sequence": degree_sequence(masks),
        "connected": len(components) == 1,
        "number_of_components": len(components),
        "components": components,
        "total_domination_number": coefficient_support[0],
        "coefficients": coefficients,
        "polynomial": polynomial_string(coefficients),
        "total_number_of_total_dominating_sets": sum(coefficients),
        "log_concavity_failures": failures,
        "unimodal": is_unimodal(coefficients),
    }


def analyze_order(order: int) -> tuple[dict[str, int], list[dict[str, object]]]:
    records = load_census(order)

    eligible_count = 0
    connected_eligible = 0
    disconnected_eligible = 0
    non_log_concave_count = 0
    connected_exceptions = 0
    disconnected_exceptions = 0
    exceptions: list[dict[str, object]] = []

    for census_line, graph6 in enumerate(records, start=1):
        graph = decode_graph6(graph6)

        if graph.order != order:
            raise AssertionError(
                f"Order {order}, line {census_line}: "
                f"decoded order {graph.order}."
            )

        masks = neighborhood_masks(graph)

        if has_isolated_vertex(masks):
            continue

        eligible_count += 1
        components = connected_components(masks)
        connected = len(components) == 1

        if connected:
            connected_eligible += 1
        else:
            disconnected_eligible += 1

        coefficients = total_domination_coefficients(masks)

        # Mathematical and implementation invariants.
        if coefficients[-1] != 1:
            raise AssertionError(
                f"{graph6}: the complete vertex set was not counted "
                "exactly once."
            )

        if has_internal_zeros(coefficients):
            raise AssertionError(
                f"{graph6}: internal zero detected in {coefficients}."
            )

        coefficient_support = support(coefficients)

        if coefficient_support is None:
            raise AssertionError(
                f"{graph6}: no total dominating set was found."
            )

        if coefficient_support[-1] != order:
            raise AssertionError(
                f"{graph6}: coefficient support does not end at order {order}."
            )

        failures = log_concavity_failures(coefficients)

        if failures:
            non_log_concave_count += 1

            if connected:
                connected_exceptions += 1
            else:
                disconnected_exceptions += 1

            exceptions.append(
                make_exception_record(
                    order=order,
                    census_line=census_line,
                    graph6=graph6,
                    graph=graph,
                    masks=masks,
                    coefficients=coefficients,
                    failures=failures,
                )
            )

    if eligible_count != EXPECTED_NO_ISOLATES[order]:
        raise AssertionError(
            f"Order {order}: expected {EXPECTED_NO_ISOLATES[order]} "
            f"graphs without isolates, obtained {eligible_count}."
        )

    summary = {
        "order": order,
        "all_graphs": len(records),
        "without_isolates": eligible_count,
        "connected_without_isolates": connected_eligible,
        "disconnected_without_isolates": disconnected_eligible,
        "non_log_concave": non_log_concave_count,
        "connected_exceptions": connected_exceptions,
        "disconnected_exceptions": disconnected_exceptions,
    }

    return summary, exceptions


def print_exception(record: dict[str, object]) -> None:
    print()
    print("=" * 88)
    print(
        f"NON-LOG-CONCAVE GRAPH: order {record['order']}, "
        f"graph6 {record['graph6']}"
    )
    print("=" * 88)
    print(f"Census line:              {record['census_line']}")
    print(f"Edges:                    {record['edges']}")
    print(f"Degree sequence:          {record['degree_sequence']}")
    print(f"Connected:                {record['connected']}")
    print(f"Number of components:     {record['number_of_components']}")
    print(f"Components:               {record['components']}")
    print(
        f"Total-domination number:  "
        f"{record['total_domination_number']}"
    )
    print(f"Coefficient vector:       {record['coefficients']}")
    print(f"D_t(G,x):                 {record['polynomial']}")
    print(
        f"Number of TDSs:           "
        f"{record['total_number_of_total_dominating_sets']}"
    )
    print(f"Unimodal:                 {record['unimodal']}")
    print("Failed inequalities:")

    for failure in record["log_concavity_failures"]:
        print(
            f"  k={failure['index']}: "
            f"{failure['coefficient']}^2 = "
            f"{failure['left_square']} < "
            f"{failure['previous_coefficient']}*"
            f"{failure['next_coefficient']} = "
            f"{failure['right_product']}"
        )

    # Machine-readable copy of the complete exception record.
    print(
        "EXCEPTION_JSON: "
        + json.dumps(record, sort_keys=True, separators=(",", ":"))
    )


def main() -> int:
    try:
        validate_integration_examples()

        summaries: list[dict[str, int]] = []
        all_exceptions: list[dict[str, object]] = []

        print("Running exhaustive census")
        print("=" * 88)

        for order in range(2, 9):
            summary, exceptions = analyze_order(order)
            summaries.append(summary)
            all_exceptions.extend(exceptions)

            print(
                f"Order {order}: examined "
                f"{summary['without_isolates']} graphs without isolates; "
                f"found {summary['non_log_concave']} "
                "non-log-concave graphs."
            )

        print()
        print("Exhaustive summary")
        print("=" * 108)
        print(
            " n |    all | no isolates | connected | disconnected | "
            "non-LC | connected non-LC | disconnected non-LC"
        )
        print("-" * 108)

        for summary in summaries:
            print(
                f"{summary['order']:2d} | "
                f"{summary['all_graphs']:6d} | "
                f"{summary['without_isolates']:11d} | "
                f"{summary['connected_without_isolates']:9d} | "
                f"{summary['disconnected_without_isolates']:12d} | "
                f"{summary['non_log_concave']:6d} | "
                f"{summary['connected_exceptions']:16d} | "
                f"{summary['disconnected_exceptions']:19d}"
            )

        for exception in all_exceptions:
            print_exception(exception)

        print()
        print("=" * 88)
        print(
            f"EXHAUSTIVE RUN COMPLETED: "
            f"{len(all_exceptions)} non-log-concave graph(s) found."
        )
        print("=" * 88)

        return 0

    except (
        AssertionError,
        FileNotFoundError,
        OSError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())