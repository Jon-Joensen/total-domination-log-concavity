SMALLEST GRAPHS WITH NON-LOG-CONCAVE TOTAL-DOMINATION POLYNOMIALS
=================================================================

Author: Jón Joensen
ORCID: https://orcid.org/0009-0000-2365-9519

This archive contains the source code, graph census files, saved computational outputs, and structural-analysis materials accompanying the manuscript:

“Smallest Graphs with Non-Log-Concave Total-Domination Polynomials and a Correction for Generalized Barbell Graphs”


1. OVERVIEW
-----------

The programs perform an exhaustive census of all finite simple unlabeled graphs without isolated vertices of orders 2 through 8.

For every eligible graph, the programs calculate its total-domination polynomial and test whether its nonzero coefficient sequence is log-concave and unimodal.

The computation establishes that:

- Every eligible graph of order at most 7 has a log-concave total-domination polynomial.
- Exactly three isomorphism classes of order 8 have non-log-concave total-domination polynomials.
- All three exceptional coefficient sequences are nevertheless unimodal.

The three exceptional graph6 records are:

GCZTfO
GQhTUg
GQhTVS


2. FILES
--------

validate_total_domination.py

A transparent implementation of total-domination coefficient enumeration. It includes hand-checkable tests on several small named graphs and can also analyse a graph supplied by its vertex and edge sets.


validate_graph6_census.py

Downloads and validates Brendan McKay’s graph6 census files for orders 2 through 8. It checks the graph6 decoder, graph orders, record counts, uniqueness, connectedness, isolated vertices, and SHA-256 hashes.


run_total_domination_census.py

The primary exhaustive Python census. It examines every graph without isolated vertices in the validated census, calculates its total-domination coefficient vector, and tests internal zeros, log-concavity, and unimodality.


independent_verification.js

An independent JavaScript implementation. It uses a separately written graph6 decoder, Boolean adjacency matrices, recursive subset generation, and independent implementations of the relevant graph and sequence tests. It compares its complete exception records with the Python results.


analyze_exception_structure.py

Performs a structural analysis of the exceptional graph GCZTfO and independently derives its total-domination polynomial using inclusion-exclusion.


first_census_output.txt

Saved output from the exhaustive Python census.


independent_verification_output.txt

Saved output from the independent JavaScript verification.


data/original/graph2.g6
data/original/graph3.g6
data/original/graph4.g6
data/original/graph5.g6
data/original/graph6.g6
data/original/graph7.g6
data/original/graph8.g6

The graph6 census files used in the computation.


3. SOFTWARE REQUIREMENTS
------------------------

The reported computation was performed using:

Python 3.12.10
Node.js 26.5.1

The programs use only the standard libraries supplied with Python and Node.js. No third-party Python or JavaScript packages are required.


4. REPRODUCTION INSTRUCTIONS
----------------------------

Run all commands from the root directory of this archive.

Step 1: Confirm the installed versions.

python --version
node --version


Step 2: Run the named-graph validation tests.

python validate_total_domination.py --self-test --show-sets

The expected final line is:

ALL SELF-TESTS PASSED: 7/7


Step 3: Download and validate the graph6 census.

python validate_graph6_census.py

This program downloads graph2.g6 through graph8.g6 from Brendan McKay’s Graph Data Collection and stores them in:

data/original/


Step 4: Run the primary exhaustive Python census.

On Windows PowerShell:

python run_total_domination_census.py 2>&1 |
    Tee-Object -FilePath first_census_output.txt

The expected final statement is:

EXHAUSTIVE RUN COMPLETED: 3 non-log-concave graph(s) found.


Step 5: Run the independent JavaScript verification.

On Windows PowerShell:

node independent_verification.js 2>&1 |
    Tee-Object -FilePath independent_verification_output.txt

The expected final statement is:

INDEPENDENT VERIFICATION PASSED


Step 6: Run the structural and inclusion-exclusion analysis.

python analyze_exception_structure.py

The expected final statement is:

ANALYTICAL COEFFICIENT CHECK PASSED


5. EXPECTED CENSUS SUMMARY
--------------------------

Order    Examined without isolated vertices    Non-log-concave
2        1                                     0
3        2                                     0
4        7                                     0
5        23                                    0
6        122                                   0
7        888                                   0
8        11,302                                3


6. EXPECTED EXCEPTION RECORDS
-----------------------------

Graph6 identifier: GCZTfO

Coefficient vector:

[0, 0, 1, 6, 40, 50, 28, 8, 1]

Total-domination polynomial:

x^2 + 6x^3 + 40x^4 + 50x^5 + 28x^6 + 8x^7 + x^8


Graph6 identifier: GQhTUg

Coefficient vector:

[0, 0, 1, 6, 42, 50, 28, 8, 1]

Total-domination polynomial:

x^2 + 6x^3 + 42x^4 + 50x^5 + 28x^6 + 8x^7 + x^8


Graph6 identifier: GQhTVS

Coefficient vector:

[0, 0, 1, 6, 37, 44, 26, 8, 1]

Total-domination polynomial:

x^2 + 6x^3 + 37x^4 + 44x^5 + 26x^6 + 8x^7 + x^8


For each exceptional graph, log-concavity fails at degree 3:

6^2 < 1 × 40
6^2 < 1 × 42
6^2 < 1 × 37


7. INDEPENDENT COMPARISON
-------------------------

The Python and JavaScript implementations produce identical canonical exception records.

The expected SHA-256 hash of the canonical representation of the three exception records is:

b4503ee2b1976209ba995c6620bc83a305498524ad99693766e78eb33fcf7d33

A reproduction should not be regarded as successful merely because it finds three exceptions. It should also reproduce the complete coefficient vectors, graph6 identifiers, edge lists, degree sequences, connectedness results, failed inequalities, and canonical exception hash.


8. SOURCE OF THE GRAPH CENSUS
-----------------------------

The graph census files were obtained from Brendan McKay’s Graph Data Collection:

https://users.cecs.anu.edu.au/~bdm/data/graphs.html

The graph6 encoding is described in:

McKay, B. D. (2022).
Description of graph6, sparse6 and digraph6 encodings.
Australian National University.
https://users.cecs.anu.edu.au/~bdm/data/formats.txt

The graph census files are third-party research data. Their inclusion here does not imply that they are covered by any licence applied to the author-written source code.


9. CITATION
-----------

If you use this code or its computational results, please cite:

Joensen, Jón.
“Smallest Graphs with Non-Log-Concave Total-Domination Polynomials and a Correction for Generalized Barbell Graphs.”

Please also cite the archived software record using its Zenodo DOI once that record has been published.


10. CONTACT
-----------

Jón Joensen
Email: joensen.jon@gmail.com
ORCID: https://orcid.org/0009-0000-2365-9519
