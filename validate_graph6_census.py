#!/usr/bin/env python3
"""
Stage 3A: download and validate Brendan McKay's graph6 censuses.

This program does NOT calculate total-domination polynomials.

It:
1. downloads the graph6 files for orders 2 through 8;
2. records their SHA-256 hashes;
3. validates an independent graph6 decoder;
4. checks line counts, uniqueness, and graph orders;
5. counts connected graphs;
6. counts graphs without isolated vertices;
7. separates connected and disconnected graphs without isolates.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass
from pathlib import Path


BASE_URL = "https://users.cecs.anu.edu.au/~bdm/data"
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

EXPECTED_CONNECTED = {
    2: 1,
    3: 2,
    4: 6,
    5: 21,
    6: 112,
    7: 853,
    8: 11117,
}


@dataclass(frozen=True)
class DecodedGraph:
    order: int
    edges: tuple[tuple[int, int], ...]


def six_bit_value(character: str) -> int:
    value = ord(character) - 63

    if not 0 <= value <= 63:
        raise ValueError(
            f"Invalid graph6 character {character!r}: "
            "every encoded character must lie between '?' and '~'."
        )

    return value


def decode_graph_order(text: str) -> tuple[int, int]:
    """
    Decode graph order.

    Return:
        (number_of_vertices, index_of_first_adjacency_character)
    """
    if not text:
        raise ValueError("Empty graph6 record.")

    values = [six_bit_value(character) for character in text]

    if values[0] != 63:
        return values[0], 1

    if len(values) < 4:
        raise ValueError("Truncated extended graph6 order field.")

    if values[1] != 63:
        order = (values[1] << 12) | (values[2] << 6) | values[3]
        return order, 4

    if len(values) < 8:
        raise ValueError("Truncated large graph6 order field.")

    order = 0
    for value in values[2:8]:
        order = (order << 6) | value

    return order, 8


def decode_graph6(record: str) -> DecodedGraph:
    """Decode one non-incremental graph6 record."""
    text = record.strip()

    if text.startswith(">>graph6<<"):
        text = text[len(">>graph6<<") :]

    if not text:
        raise ValueError("Empty graph6 record.")

    if text.startswith(":"):
        raise ValueError("sparse6 input is not supported.")

    if text.startswith("&"):
        raise ValueError("digraph6 input is not supported.")

    order, data_start = decode_graph_order(text)
    adjacency_text = text[data_start:]

    number_of_bits = order * (order - 1) // 2
    expected_characters = (number_of_bits + 5) // 6

    if len(adjacency_text) != expected_characters:
        raise ValueError(
            f"Order {order} requires {expected_characters} adjacency "
            f"characters, but the record contains {len(adjacency_text)}."
        )

    bits: list[int] = []

    for character in adjacency_text:
        value = six_bit_value(character)
        bits.extend((value >> shift) & 1 for shift in range(5, -1, -1))

    padding = bits[number_of_bits:]

    if any(padding):
        raise ValueError("Nonzero padding bits in graph6 record.")

    edges: list[tuple[int, int]] = []
    bit_index = 0

    # Official graph6 order:
    # (0,1), (0,2), (1,2), (0,3), (1,3), (2,3), ...
    for larger_vertex in range(1, order):
        for smaller_vertex in range(larger_vertex):
            if bits[bit_index]:
                edges.append((smaller_vertex, larger_vertex))
            bit_index += 1

    return DecodedGraph(order=order, edges=tuple(edges))


def degree_sequence(graph: DecodedGraph) -> tuple[int, ...]:
    degrees = [0] * graph.order

    for u, v in graph.edges:
        degrees[u] += 1
        degrees[v] += 1

    return tuple(sorted(degrees, reverse=True))


def has_isolated_vertex(graph: DecodedGraph) -> bool:
    if graph.order == 0:
        return False

    degrees = [0] * graph.order

    for u, v in graph.edges:
        degrees[u] += 1
        degrees[v] += 1

    return any(degree == 0 for degree in degrees)


def is_connected(graph: DecodedGraph) -> bool:
    if graph.order == 0:
        return True

    adjacency = [set() for _ in range(graph.order)]

    for u, v in graph.edges:
        adjacency[u].add(v)
        adjacency[v].add(u)

    visited = {0}
    queue = deque([0])

    while queue:
        vertex = queue.popleft()

        for neighbor in adjacency[vertex]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return len(visited) == graph.order


def validate_known_graph6_examples() -> None:
    """
    Validate the decoder against graph6 strings whose graphs can be
    determined by hand.
    """
    examples = [
        ("A?", 2, (), "empty graph on two vertices"),
        ("A_", 2, ((0, 1),), "K2"),
        (
            "Bw",
            3,
            ((0, 1), (0, 2), (1, 2)),
            "K3",
        ),
        (
            "Ch",
            4,
            ((0, 1), (1, 2), (2, 3)),
            "P4",
        ),
        (
            "Cl",
            4,
            ((0, 1), (0, 3), (1, 2), (2, 3)),
            "C4",
        ),
        (
            "C~",
            4,
            (
                (0, 1),
                (0, 2),
                (0, 3),
                (1, 2),
                (1, 3),
                (2, 3),
            ),
            "K4",
        ),
    ]

    print("Graph6 decoder tests")
    print("=" * 88)

    for code, expected_order, expected_edges, description in examples:
        graph = decode_graph6(code)

        if graph.order != expected_order:
            raise AssertionError(
                f"{code}: expected order {expected_order}, "
                f"obtained {graph.order}."
            )

        if tuple(sorted(graph.edges)) != tuple(sorted(expected_edges)):
            raise AssertionError(
                f"{code}: expected edges {tuple(sorted(expected_edges))}, "
                f"obtained {tuple(sorted(graph.edges))}."
            )

        print(
            f"PASS  {code:<4} {description:<30} "
            f"order={graph.order}, edges={graph.edges}"
        )

    print(f"ALL GRAPH6 DECODER TESTS PASSED: {len(examples)}/{len(examples)}")
    print()


def download_census(order: int) -> tuple[bytes, Path, str]:
    """Download one census, preserving the exact bytes used for hashing."""
    url = f"{BASE_URL}/graph{order}.g6"
    destination = DATA_DIRECTORY / f"graph{order}.g6"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "total-domination-polynomial-research/1.0 "
                "(academic reproducibility check)"
            )
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Download of {url} returned HTTP {response.status}."
                )
            downloaded = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not download {url}: {exc}") from exc

    if not downloaded:
        raise RuntimeError(f"Downloaded file from {url} is empty.")

    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        existing = destination.read_bytes()

        if existing != downloaded:
            raise RuntimeError(
                f"{destination} already exists but differs from the "
                "current download. It was not overwritten."
            )

        status = "existing file matches download"
    else:
        destination.write_bytes(downloaded)
        status = "download saved"

    return downloaded, destination, status


def parse_census(raw_data: bytes, source_name: str) -> list[str]:
    try:
        text = raw_data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source_name} is not ASCII graph6 data.") from exc

    records = [line.strip() for line in text.splitlines() if line.strip()]

    if not records:
        raise ValueError(f"{source_name} contains no graph records.")

    return records


def analyze_census(order: int) -> dict[str, object]:
    raw_data, path, download_status = download_census(order)
    records = parse_census(raw_data, str(path))

    expected_all = EXPECTED_ALL[order]

    if len(records) != expected_all:
        raise AssertionError(
            f"Order {order}: expected {expected_all} records, "
            f"obtained {len(records)}."
        )

    unique_count = len(set(records))

    if unique_count != len(records):
        raise AssertionError(
            f"Order {order}: found {len(records) - unique_count} "
            "duplicate graph6 records."
        )

    connected_count = 0
    no_isolates_count = 0
    disconnected_no_isolates_count = 0

    for line_number, record in enumerate(records, start=1):
        try:
            graph = decode_graph6(record)
        except ValueError as exc:
            raise ValueError(
                f"{path}, line {line_number}: {exc}"
            ) from exc

        if graph.order != order:
            raise AssertionError(
                f"{path}, line {line_number}: expected order {order}, "
                f"decoded order {graph.order}."
            )

        connected = is_connected(graph)
        no_isolates = not has_isolated_vertex(graph)

        if connected:
            connected_count += 1

        if no_isolates:
            no_isolates_count += 1

            if not connected:
                disconnected_no_isolates_count += 1

    if connected_count != EXPECTED_CONNECTED[order]:
        raise AssertionError(
            f"Order {order}: expected {EXPECTED_CONNECTED[order]} "
            f"connected graphs, obtained {connected_count}."
        )

    sha256 = hashlib.sha256(raw_data).hexdigest()

    return {
        "order": order,
        "url": f"{BASE_URL}/graph{order}.g6",
        "path": str(path.resolve()),
        "download_status": download_status,
        "bytes": len(raw_data),
        "sha256": sha256,
        "all": len(records),
        "unique": unique_count,
        "connected": connected_count,
        "disconnected": len(records) - connected_count,
        "no_isolates": no_isolates_count,
        "connected_no_isolates": connected_count,
        "disconnected_no_isolates": disconnected_no_isolates_count,
        "first_record": records[0],
        "last_record": records[-1],
    }


def main() -> int:
    try:
        validate_known_graph6_examples()

        print("Downloading and validating authoritative censuses")
        print("=" * 88)

        results = []

        for order in range(2, 9):
            result = analyze_census(order)
            results.append(result)

            print(f"Order {order}: PASS")
            print(f"  URL:              {result['url']}")
            print(f"  Local path:       {result['path']}")
            print(f"  Status:           {result['download_status']}")
            print(f"  File bytes:       {result['bytes']}")
            print(f"  SHA-256:          {result['sha256']}")
            print(f"  First record:     {result['first_record']}")
            print(f"  Last record:      {result['last_record']}")
            print()

        print("Validated census counts")
        print("=" * 88)
        print(
            " n |    all | connected | disconnected | no isolates | "
            "connected no isolates | disconnected no isolates"
        )
        print("-" * 88)

        for result in results:
            print(
                f"{result['order']:2d} | "
                f"{result['all']:6d} | "
                f"{result['connected']:9d} | "
                f"{result['disconnected']:12d} | "
                f"{result['no_isolates']:11d} | "
                f"{result['connected_no_isolates']:21d} | "
                f"{result['disconnected_no_isolates']:24d}"
            )

        print()
        print("ALL CENSUS AND GRAPH6 VALIDATION CHECKS PASSED")
        return 0

    except (AssertionError, OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())