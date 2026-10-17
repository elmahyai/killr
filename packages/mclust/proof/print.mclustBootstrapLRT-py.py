"""Proof: Python print.mclustBootstrapLRT on the same fixed inputs as the R proof.

Writes the printed text to stdout and the median of 20 timed calls (ms) to stderr.
"""

import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.bootstrap_family import print_mclustBootstrapLRT


def _boot(nrow, ncol, start, step):
    values = [start + step * i for i in range(nrow * ncol)]
    # R matrices are column-major: column j holds values j*nrow .. (j+1)*nrow-1.
    return [[values[j * nrow + i] for j in range(ncol)] for i in range(nrow)]


CASE_A = {
    "G": [1, 2, 3],
    "modelName": "EEE",
    "obs": [12.3456789, 3.2, 0.000123],
    "boot": _boot(20, 3, 0.5, 0.25),
    "p.value": [0.001, 0.2, 1.0],
}

CASE_B = {
    "G": [1, 2],
    "modelName": "VVV",
    "obs": [1e-10, 2.5],
    "boot": _boot(5, 2, 1.0, 0.5),
    "p.value": [0.5, 0.04],
}


def one():
    return print_mclustBootstrapLRT(CASE_A) + print_mclustBootstrapLRT(CASE_B)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

sys.stdout.write("\n".join(value.splitlines()) + "\n")
sys.stderr.write("%.17g\n" % statistics.median(elapsed))
