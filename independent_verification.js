"use strict";

/*
Independent verification of the total-domination census.

This program does not import or execute any Python code. It uses:
- an independently written graph6 parser;
- Boolean adjacency matrices;
- recursive subset generation;
- an independent connectivity routine;
- exact comparison with the Python result records.
*/

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const DATA_DIRECTORY = path.join("data", "original");
const FIRST_OUTPUT = "first_census_output.txt";

const EXPECTED_ALL = new Map([
    [2, 2],
    [3, 4],
    [4, 11],
    [5, 34],
    [6, 156],
    [7, 1044],
    [8, 12346],
]);

const EXPECTED_NO_ISOLATES = new Map([
    [2, 1],
    [3, 2],
    [4, 7],
    [5, 23],
    [6, 122],
    [7, 888],
    [8, 11302],
]);

const PYTHON_SUMMARY = [
    {
        order: 2,
        all: 2,
        noIsolates: 1,
        connected: 1,
        disconnected: 0,
        nonLogConcave: 0,
        connectedExceptions: 0,
        disconnectedExceptions: 0,
    },
    {
        order: 3,
        all: 4,
        noIsolates: 2,
        connected: 2,
        disconnected: 0,
        nonLogConcave: 0,
        connectedExceptions: 0,
        disconnectedExceptions: 0,
    },
    {
        order: 4,
        all: 11,
        noIsolates: 7,
        connected: 6,
        disconnected: 1,
        nonLogConcave: 0,
        connectedExceptions: 0,
        disconnectedExceptions: 0,
    },
    {
        order: 5,
        all: 34,
        noIsolates: 23,
        connected: 21,
        disconnected: 2,
        nonLogConcave: 0,
        connectedExceptions: 0,
        disconnectedExceptions: 0,
    },
    {
        order: 6,
        all: 156,
        noIsolates: 122,
        connected: 112,
        disconnected: 10,
        nonLogConcave: 0,
        connectedExceptions: 0,
        disconnectedExceptions: 0,
    },
    {
        order: 7,
        all: 1044,
        noIsolates: 888,
        connected: 853,
        disconnected: 35,
        nonLogConcave: 0,
        connectedExceptions: 0,
        disconnectedExceptions: 0,
    },
    {
        order: 8,
        all: 12346,
        noIsolates: 11302,
        connected: 11117,
        disconnected: 185,
        nonLogConcave: 3,
        connectedExceptions: 3,
        disconnectedExceptions: 0,
    },
];

function readTextFile(filename) {
    const buffer = fs.readFileSync(filename);

    // Windows PowerShell 5.1 commonly writes Tee-Object output as UTF-16LE.
    if (
        buffer.length >= 2 &&
        buffer[0] === 0xff &&
        buffer[1] === 0xfe
    ) {
        return buffer
            .subarray(2)
            .toString("utf16le")
            .replace(/^\uFEFF/, "");
    }

    return buffer.toString("utf8").replace(/^\uFEFF/, "");
}

function requireCondition(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function sixBitValue(character) {
    const value = character.charCodeAt(0) - 63;

    requireCondition(
        value >= 0 && value <= 63,
        `Invalid graph6 character ${JSON.stringify(character)}.`
    );

    return value;
}

function decodeOrder(text) {
    const values = Array.from(text, sixBitValue);

    requireCondition(values.length > 0, "Empty graph6 record.");

    if (values[0] !== 63) {
        return { order: values[0], dataStart: 1 };
    }

    requireCondition(
        values.length >= 4,
        "Truncated extended graph6 order."
    );

    if (values[1] !== 63) {
        const order =
            values[1] * 64 * 64 +
            values[2] * 64 +
            values[3];

        return { order, dataStart: 4 };
    }

    requireCondition(
        values.length >= 8,
        "Truncated large graph6 order."
    );

    let order = 0;

    for (const value of values.slice(2, 8)) {
        order = order * 64 + value;
    }

    return { order, dataStart: 8 };
}

function decodeGraph6(record) {
    let text = record.trim();

    if (text.startsWith(">>graph6<<")) {
        text = text.slice(">>graph6<<".length);
    }

    requireCondition(text.length > 0, "Empty graph6 record.");
    requireCondition(!text.startsWith(":"), "sparse6 is unsupported.");
    requireCondition(!text.startsWith("&"), "digraph6 is unsupported.");

    const { order, dataStart } = decodeOrder(text);
    const data = text.slice(dataStart);
    const neededBits = (order * (order - 1)) / 2;
    const neededCharacters = Math.ceil(neededBits / 6);

    requireCondition(
        data.length === neededCharacters,
        `Order ${order} requires ${neededCharacters} adjacency ` +
        `characters, found ${data.length}.`
    );

    const bits = [];

    for (const character of data) {
        const value = sixBitValue(character);

        for (let shift = 5; shift >= 0; shift -= 1) {
            bits.push((value >> shift) & 1);
        }
    }

    for (const paddingBit of bits.slice(neededBits)) {
        requireCondition(
            paddingBit === 0,
            "Nonzero graph6 padding bit."
        );
    }

    const adjacency = Array.from(
        { length: order },
        () => Array(order).fill(false)
    );

    const edges = [];
    let bitIndex = 0;

    for (let larger = 1; larger < order; larger += 1) {
        for (let smaller = 0; smaller < larger; smaller += 1) {
            if (bits[bitIndex] === 1) {
                adjacency[smaller][larger] = true;
                adjacency[larger][smaller] = true;
                edges.push([smaller, larger]);
            }

            bitIndex += 1;
        }
    }

    return { order, adjacency, edges };
}

function hasIsolatedVertex(graph) {
    return graph.adjacency.some(
        row => !row.some(isAdjacent => isAdjacent)
    );
}

function connectedComponents(graph) {
    const unseen = new Set(
        Array.from({ length: graph.order }, (_, index) => index)
    );

    const components = [];

    while (unseen.size > 0) {
        const start = Math.min(...unseen);
        unseen.delete(start);

        const component = [];
        const stack = [start];

        while (stack.length > 0) {
            const vertex = stack.pop();
            component.push(vertex);

            for (let neighbor = 0; neighbor < graph.order; neighbor += 1) {
                if (
                    graph.adjacency[vertex][neighbor] &&
                    unseen.has(neighbor)
                ) {
                    unseen.delete(neighbor);
                    stack.push(neighbor);
                }
            }
        }

        component.sort((a, b) => a - b);
        components.push(component);
    }

    return components;
}

function totalDominationCoefficients(graph) {
    const coefficients = Array(graph.order + 1).fill(0);
    const selected = Array(graph.order).fill(false);

    function isTotalDominating() {
        for (let vertex = 0; vertex < graph.order; vertex += 1) {
            let hasSelectedNeighbor = false;

            for (
                let neighbor = 0;
                neighbor < graph.order;
                neighbor += 1
            ) {
                if (
                    graph.adjacency[vertex][neighbor] &&
                    selected[neighbor]
                ) {
                    hasSelectedNeighbor = true;
                    break;
                }
            }

            if (!hasSelectedNeighbor) {
                return false;
            }
        }

        return true;
    }

    function enumerate(vertex, cardinality) {
        if (vertex === graph.order) {
            if (isTotalDominating()) {
                coefficients[cardinality] += 1;
            }
            return;
        }

        selected[vertex] = false;
        enumerate(vertex + 1, cardinality);

        selected[vertex] = true;
        enumerate(vertex + 1, cardinality + 1);

        selected[vertex] = false;
    }

    enumerate(0, 0);
    return coefficients;
}

function coefficientSupport(coefficients) {
    const nonzero = [];

    coefficients.forEach((coefficient, index) => {
        if (coefficient !== 0) {
            nonzero.push(index);
        }
    });

    if (nonzero.length === 0) {
        return null;
    }

    return [nonzero[0], nonzero[nonzero.length - 1]];
}

function hasInternalZeros(coefficients) {
    const support = coefficientSupport(coefficients);

    if (support === null) {
        return false;
    }

    const [first, last] = support;

    for (let index = first; index <= last; index += 1) {
        if (coefficients[index] === 0) {
            return true;
        }
    }

    return false;
}

function logConcavityFailures(coefficients) {
    const support = coefficientSupport(coefficients);

    if (support === null) {
        return [];
    }

    const [first, last] = support;
    const failures = [];

    for (let index = first + 1; index < last; index += 1) {
        const leftSquare = coefficients[index] ** 2;
        const rightProduct =
            coefficients[index - 1] * coefficients[index + 1];

        if (leftSquare < rightProduct) {
            failures.push({
                coefficient: coefficients[index],
                index,
                left_square: leftSquare,
                next_coefficient: coefficients[index + 1],
                previous_coefficient: coefficients[index - 1],
                right_product: rightProduct,
            });
        }
    }

    return failures;
}

function isUnimodal(coefficients) {
    const support = coefficientSupport(coefficients);

    if (support === null) {
        return null;
    }

    const values = coefficients.slice(support[0], support[1] + 1);

    for (let mode = 0; mode < values.length; mode += 1) {
        let valid = true;

        for (let index = 0; index < mode; index += 1) {
            if (values[index] > values[index + 1]) {
                valid = false;
            }
        }

        for (
            let index = mode;
            index < values.length - 1;
            index += 1
        ) {
            if (values[index] < values[index + 1]) {
                valid = false;
            }
        }

        if (valid) {
            return true;
        }
    }

    return false;
}

function degreeSequence(graph) {
    return graph.adjacency
        .map(row => row.filter(Boolean).length)
        .sort((a, b) => b - a);
}

function canonicalEdges(edges) {
    return edges
        .map(([u, v]) => [Math.min(u, v), Math.max(u, v)])
        .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
}

function validateIntegrationExamples() {
    const examples = [
        ["K2", "A_", [0, 0, 1]],
        ["K3", "Bw", [0, 0, 3, 1]],
        ["P4", "Ch", [0, 0, 1, 2, 1]],
        ["C4", "Cl", [0, 0, 4, 4, 1]],
        ["K1,3", "Cs", [0, 0, 3, 3, 1]],
        ["K2,2", "C]", [0, 0, 4, 4, 1]],
    ];

    console.log("Independent JavaScript integration tests");
    console.log("=".repeat(88));

    for (const [name, graph6, expected] of examples) {
        const graph = decodeGraph6(graph6);
        const obtained = totalDominationCoefficients(graph);

        requireCondition(
            JSON.stringify(obtained) === JSON.stringify(expected),
            `${name}: expected ${JSON.stringify(expected)}, ` +
            `obtained ${JSON.stringify(obtained)}.`
        );

        console.log(
            `PASS  ${name.padEnd(8)} graph6=${graph6.padEnd(4)} ` +
            `coefficients=${JSON.stringify(obtained)}`
        );
    }

    console.log(
        `ALL JAVASCRIPT INTEGRATION TESTS PASSED: ` +
        `${examples.length}/${examples.length}`
    );
    console.log();
}

function loadRecords(order) {
    const filename = path.join(
        DATA_DIRECTORY,
        `graph${order}.g6`
    );

    requireCondition(
        fs.existsSync(filename),
        `Missing ${filename}.`
    );

    const records = fs
        .readFileSync(filename, "ascii")
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(line => line.length > 0);

    requireCondition(
        records.length === EXPECTED_ALL.get(order),
        `Order ${order}: expected ${EXPECTED_ALL.get(order)} records, ` +
        `found ${records.length}.`
    );

    requireCondition(
        new Set(records).size === records.length,
        `Order ${order}: duplicate records found.`
    );

    return records;
}

function analyzeOrder(order) {
    const records = loadRecords(order);

    let noIsolates = 0;
    let connectedCount = 0;
    let disconnectedCount = 0;
    let connectedExceptions = 0;
    let disconnectedExceptions = 0;

    const exceptions = [];

    records.forEach((graph6, zeroBasedLine) => {
        const graph = decodeGraph6(graph6);

        requireCondition(
            graph.order === order,
            `${graph6}: expected order ${order}, decoded ${graph.order}.`
        );

        if (hasIsolatedVertex(graph)) {
            return;
        }

        noIsolates += 1;

        const components = connectedComponents(graph);
        const connected = components.length === 1;

        if (connected) {
            connectedCount += 1;
        } else {
            disconnectedCount += 1;
        }

        const coefficients = totalDominationCoefficients(graph);

        requireCondition(
            coefficients[order] === 1,
            `${graph6}: full vertex set was not counted once.`
        );

        requireCondition(
            !hasInternalZeros(coefficients),
            `${graph6}: internal coefficient zero detected.`
        );

        const support = coefficientSupport(coefficients);

        requireCondition(
            support !== null && support[1] === order,
            `${graph6}: invalid coefficient support.`
        );

        const failures = logConcavityFailures(coefficients);

        if (failures.length > 0) {
            if (connected) {
                connectedExceptions += 1;
            } else {
                disconnectedExceptions += 1;
            }

            exceptions.push({
                census_line: zeroBasedLine + 1,
                coefficients,
                components,
                connected,
                degree_sequence: degreeSequence(graph),
                edges: canonicalEdges(graph.edges),
                graph6,
                log_concavity_failures: failures,
                number_of_components: components.length,
                order,
                total_domination_number: support[0],
                total_number_of_total_dominating_sets:
                    coefficients.reduce((sum, value) => sum + value, 0),
                unimodal: isUnimodal(coefficients),
            });
        }
    });

    requireCondition(
        noIsolates === EXPECTED_NO_ISOLATES.get(order),
        `Order ${order}: expected ${EXPECTED_NO_ISOLATES.get(order)} ` +
        `graphs without isolates, found ${noIsolates}.`
    );

    return {
        summary: {
            order,
            all: records.length,
            noIsolates,
            connected: connectedCount,
            disconnected: disconnectedCount,
            nonLogConcave: exceptions.length,
            connectedExceptions,
            disconnectedExceptions,
        },
        exceptions,
    };
}

function readPythonExceptions() {
    requireCondition(
        fs.existsSync(FIRST_OUTPUT),
        `Missing ${FIRST_OUTPUT}.`
    );

    const prefix = "EXCEPTION_JSON: ";

    return readTextFile(FIRST_OUTPUT)
        .split(/\r?\n/)
        .filter(line => line.startsWith(prefix))
        .map(line => JSON.parse(line.slice(prefix.length)));
}

function canonicalException(record) {
    return {
        order: record.order,
        census_line: record.census_line,
        graph6: record.graph6,
        edges: canonicalEdges(record.edges),
        degree_sequence: record.degree_sequence,
        connected: record.connected,
        number_of_components: record.number_of_components,
        components: record.components,
        total_domination_number: record.total_domination_number,
        coefficients: record.coefficients,
        total_number_of_total_dominating_sets:
            record.total_number_of_total_dominating_sets,
        log_concavity_failures: record.log_concavity_failures,
        unimodal: record.unimodal,
    };
}

function canonicalResult(records) {
    return records
        .map(canonicalException)
        .sort((a, b) => a.graph6.localeCompare(b.graph6));
}

function sha256(text) {
    return crypto
        .createHash("sha256")
        .update(text, "utf8")
        .digest("hex");
}

function main() {
    validateIntegrationExamples();

    console.log("Running independent JavaScript census");
    console.log("=".repeat(88));

    const summaries = [];
    const javascriptExceptions = [];

    for (let order = 2; order <= 8; order += 1) {
        const result = analyzeOrder(order);
        summaries.push(result.summary);
        javascriptExceptions.push(...result.exceptions);

        console.log(
            `Order ${order}: examined ${result.summary.noIsolates}; ` +
            `found ${result.summary.nonLogConcave} non-log-concave.`
        );
    }

    requireCondition(
        JSON.stringify(summaries) === JSON.stringify(PYTHON_SUMMARY),
        "JavaScript and Python census summaries disagree.\n" +
        `JavaScript: ${JSON.stringify(summaries)}\n` +
        `Python:     ${JSON.stringify(PYTHON_SUMMARY)}`
    );

    const pythonExceptions = readPythonExceptions();

    requireCondition(
        pythonExceptions.length > 0,
        "No Python EXCEPTION_JSON records were found."
    );

    const canonicalPython = canonicalResult(pythonExceptions);
    const canonicalJavaScript = canonicalResult(javascriptExceptions);

    const pythonText = JSON.stringify(canonicalPython);
    const javascriptText = JSON.stringify(canonicalJavaScript);

    const pythonHash = sha256(pythonText);
    const javascriptHash = sha256(javascriptText);

    console.log();
    console.log("Independent comparison");
    console.log("=".repeat(88));
    console.log(`Python exception records:     ${canonicalPython.length}`);
    console.log(`JavaScript exception records: ${canonicalJavaScript.length}`);
    console.log(`Python canonical SHA-256:     ${pythonHash}`);
    console.log(`JavaScript canonical SHA-256: ${javascriptHash}`);

    requireCondition(
        pythonText === javascriptText,
        "Canonical Python and JavaScript exception records disagree."
    );

    requireCondition(
        pythonHash === javascriptHash,
        "Canonical result hashes disagree."
    );

    console.log();

    for (const record of canonicalJavaScript) {
        console.log(
            "INDEPENDENT_EXCEPTION_JSON: " +
            JSON.stringify(record)
        );
    }

    console.log();
    console.log("=".repeat(88));
    console.log("INDEPENDENT VERIFICATION PASSED");
    console.log("Python and JavaScript summaries agree.");
    console.log("Canonical exception records and SHA-256 hashes agree.");
    console.log("=".repeat(88));
}

try {
    main();
} catch (error) {
    console.error(`ERROR: ${error.message}`);
    process.exitCode = 1;
}