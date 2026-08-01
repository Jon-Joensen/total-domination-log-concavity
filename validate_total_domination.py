#!/usr/bin/env python3
"""
Transparent validation program for total-domination polynomials.

Examples:
    python validate_total_domination.py --self-test
    python validate_total_domination.py --self-test --show-sets
    python validate_total_domination.py --vertices 4 --edges "0-1,1-2,2-3"
"""

from __future__ import annotations

import argparse
import itertools
import sys
from collections.abc import Iterable


Edge = tuple[int, int]


def validate_graph(n: int, edges: Iterable[Edge]) -> tuple[Edge, ...]:
    """Validate and normalize a finite simple graph on vertices 0,...,n-1."""
    if n < 0:
        raise ValueError("The number of vertices cannot be negative.")

    normalized: set[Edge] = set()

    for raw_u, raw_v in edges:
        u, v = int(raw_u), int(raw_v)

        if not (0 <= u < n and 0 <= v < n):
            raise ValueError(
                f"Edge ({u}, {v}) uses a vertex outside the range 0,...,{n - 1}."
            )

        if u == v:
            raise ValueError(
                f"Edge ({u}, {v}) is a loop. Only simple graphs are supported."
            )

        edge = (min(u, v), max(u, v))

        if edge in normalized:
            raise ValueError(f"Duplicate edge detected: {edge}.")

        normalized.add(edge)

    return tuple(sorted(normalized))


def parse_edge_list(text: str) -> tuple[Edge, ...]:
    """
    Parse an edge list such as:
        0-1, 1-2, 2-3

    An empty string represents an edgeless graph.
    """
    text = text.strip()

    if not text:
        return ()

    edges: list[Edge] = []

    for item in text.split(","):
        item = item.strip()
        parts = item.split("-")

        if len(parts) != 2:
            raise ValueError(
                f"Cannot parse edge {item!r}. Use syntax such as 0-1,1-2,2-3."
            )

        try:
            u = int(parts[0].strip())
            v = int(parts[1].strip())
        except ValueError as exc:
            raise ValueError(
                f"Both endpoints of {item!r} must be integers."
            ) from exc

        edges.append((u, v))

    return tuple(edges)


def build_neighborhoods(n: int, edges: Iterable[Edge]) -> tuple[frozenset[int], ...]:
    """Construct the open neighbourhood N(v) of each vertex."""
    neighborhoods = [set() for _ in range(n)]

    for u, v in edges:
        neighborhoods[u].add(v)
        neighborhoods[v].add(u)

    return tuple(frozenset(neighbors) for neighbors in neighborhoods)


def is_total_dominating_set(
    subset: frozenset[int],
    neighborhoods: tuple[frozenset[int], ...],
) -> bool:
    """
    Return True exactly when every vertex has a neighbour in subset.

    Notice that a vertex does not dominate itself.
    """
    return all(bool(neighbors & subset) for neighbors in neighborhoods)


def enumerate_total_dominating_sets(
    n: int,
    edges: Iterable[Edge],
) -> tuple[list[int], dict[int, list[tuple[int, ...]]]]:
    """
    Enumerate every vertex subset and count total dominating sets by size.

    coefficients[k] is d_t(G,k).
    sets_by_size[k] contains the actual sets, for auditing.
    """
    normalized_edges = validate_graph(n, edges)
    neighborhoods = build_neighborhoods(n, normalized_edges)

    coefficients = [0] * (n + 1)
    sets_by_size: dict[int, list[tuple[int, ...]]] = {
        k: [] for k in range(n + 1)
    }

    vertices = range(n)

    for k in range(n + 1):
        for candidate in itertools.combinations(vertices, k):
            subset = frozenset(candidate)

            if is_total_dominating_set(subset, neighborhoods):
                coefficients[k] += 1
                sets_by_size[k].append(candidate)

    return coefficients, sets_by_size


def nonzero_support(coefficients: list[int]) -> tuple[int, int] | None:
    """Return the first and last nonzero indices, or None for the zero polynomial."""
    indices = [i for i, value in enumerate(coefficients) if value != 0]

    if not indices:
        return None

    return indices[0], indices[-1]


def has_internal_zeros(coefficients: list[int]) -> bool:
    """Check whether a zero occurs between two nonzero coefficients."""
    support = nonzero_support(coefficients)

    if support is None:
        return False

    first, last = support
    return any(coefficients[k] == 0 for k in range(first, last + 1))


def log_concavity_failures(
    coefficients: list[int],
) -> list[tuple[int, int, int]]:
    """
    Return each failed inequality as:
        (k, coefficients[k]^2, coefficients[k-1]*coefficients[k+1])
    """
    support = nonzero_support(coefficients)

    if support is None:
        return []

    first, last = support
    failures: list[tuple[int, int, int]] = []

    for k in range(first + 1, last):
        left = coefficients[k] ** 2
        right = coefficients[k - 1] * coefficients[k + 1]

        if left < right:
            failures.append((k, left, right))

    return failures


def is_unimodal(coefficients: list[int]) -> bool | None:
    """
    Test unimodality on the nonzero support.

    Return None for the zero polynomial.
    """
    support = nonzero_support(coefficients)

    if support is None:
        return None

    first, last = support
    values = coefficients[first : last + 1]

    for mode in range(len(values)):
        nondecreasing = all(
            values[i] <= values[i + 1] for i in range(mode)
        )
        nonincreasing = all(
            values[i] >= values[i + 1]
            for i in range(mode, len(values) - 1)
        )

        if nondecreasing and nonincreasing:
            return True

    return False


def polynomial_string(coefficients: list[int]) -> str:
    """Format a coefficient vector as a polynomial in ascending degree."""
    terms: list[str] = []

    for exponent, coefficient in enumerate(coefficients):
        if coefficient == 0:
            continue

        if exponent == 0:
            variable_part = ""
        elif exponent == 1:
            variable_part = "x"
        else:
            variable_part = f"x^{exponent}"

        if coefficient == 1 and variable_part:
            term = variable_part
        else:
            term = f"{coefficient}{variable_part}"

        terms.append(term)

    return " + ".join(terms) if terms else "0"


def analyze_graph(
    name: str,
    n: int,
    edges: Iterable[Edge],
    show_sets: bool = False,
) -> list[int]:
    """Analyze and print one graph."""
    normalized_edges = validate_graph(n, edges)
    neighborhoods = build_neighborhoods(n, normalized_edges)
    coefficients, sets_by_size = enumerate_total_dominating_sets(
        n, normalized_edges
    )

    support = nonzero_support(coefficients)
    failures = log_concavity_failures(coefficients)
    unimodal = is_unimodal(coefficients)

    print(f"Graph: {name}")
    print(f"Vertices: {list(range(n))}")
    print(f"Edges: {list(normalized_edges)}")
    print(
        "Open neighborhoods: "
        + str({v: sorted(neighborhoods[v]) for v in range(n)})
    )
    print(f"Coefficient vector [d_t(G,0),...,d_t(G,n)]: {coefficients}")
    print(f"D_t(G,x) = {polynomial_string(coefficients)}")

    if support is None:
        print("Total-domination number: undefined")
        print("Internal zeros: not applicable")
        print("Log-concave on nonzero support: not applicable")
        print("Unimodal on nonzero support: not applicable")
    else:
        print(f"Total-domination number: {support[0]}")
        print(f"Internal zeros: {has_internal_zeros(coefficients)}")
        print(f"Log-concave on nonzero support: {not failures}")
        print(f"Unimodal on nonzero support: {unimodal}")

        if failures:
            print("Failed log-concavity inequalities:")
            for k, left, right in failures:
                print(
                    f"  k={k}: d_t(G,{k})^2 = {left} "
                    f"< d_t(G,{k - 1})d_t(G,{k + 1}) = {right}"
                )

    if show_sets:
        print("Total dominating sets:")
        found_any = False

        for k in range(n + 1):
            if sets_by_size[k]:
                found_any = True
                print(f"  size {k}: {sets_by_size[k]}")

        if not found_any:
            print("  none")

    print("-" * 72)
    return coefficients


def run_self_tests(show_sets: bool) -> None:
    """
    Run named graphs with independently specified expected coefficients.

    Any disagreement raises AssertionError and terminates with a nonzero status.
    """
    tests = [
        (
            "K2",
            2,
            ((0, 1),),
            [0, 0, 1],
        ),
        (
            "K3",
            3,
            ((0, 1), (0, 2), (1, 2)),
            [0, 0, 3, 1],
        ),
        (
            "P3",
            3,
            ((0, 1), (1, 2)),
            [0, 0, 2, 1],
        ),
        (
            "P4",
            4,
            ((0, 1), (1, 2), (2, 3)),
            [0, 0, 1, 2, 1],
        ),
        (
            "C4",
            4,
            ((0, 1), (1, 2), (2, 3), (3, 0)),
            [0, 0, 4, 4, 1],
        ),
        (
            "K1,3",
            4,
            ((0, 1), (0, 2), (0, 3)),
            [0, 0, 3, 3, 1],
        ),
        (
            "K2,2",
            4,
            ((0, 2), (0, 3), (1, 2), (1, 3)),
            [0, 0, 4, 4, 1],
        ),
    ]

    print("Running named-graph validation suite")
    print("=" * 72)

    passed = 0

    for name, n, edges, expected in tests:
        actual = analyze_graph(name, n, edges, show_sets=show_sets)

        if actual != expected:
            raise AssertionError(
                f"{name} failed:\n"
                f"  expected {expected}\n"
                f"  obtained {actual}"
            )

        if has_internal_zeros(actual):
            raise AssertionError(f"{name} unexpectedly has internal zeros.")

        if log_concavity_failures(actual):
            raise AssertionError(f"{name} unexpectedly failed log-concavity.")

        if is_unimodal(actual) is not True:
            raise AssertionError(f"{name} unexpectedly failed unimodality.")

        print(f"SELF-TEST PASSED: {name}")
        print("=" * 72)
        passed += 1

    print(f"ALL SELF-TESTS PASSED: {passed}/{len(tests)}")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enumerate total dominating sets of a finite simple graph."
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--self-test",
        action="store_true",
        help="Run the named-graph validation suite.",
    )
    mode.add_argument(
        "--vertices",
        type=int,
        metavar="N",
        help="Analyze a graph with vertices 0,...,N-1.",
    )

    parser.add_argument(
        "--edges",
        default="",
        help='Comma-separated edges, for example "0-1,1-2,2-3".',
    )
    parser.add_argument(
        "--name",
        default="input graph",
        help="Optional name for a graph supplied on the command line.",
    )
    parser.add_argument(
        "--show-sets",
        action="store_true",
        help="Print every total dominating set.",
    )

    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    try:
        if args.self_test:
            run_self_tests(show_sets=args.show_sets)
        else:
            edges = parse_edge_list(args.edges)
            analyze_graph(
                name=args.name,
                n=args.vertices,
                edges=edges,
                show_sets=args.show_sets,
            )

    except (ValueError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())