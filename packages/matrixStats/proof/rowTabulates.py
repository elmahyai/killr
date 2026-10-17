import statistics
import subprocess
import time
from pathlib import Path

import numpy as np
from matrixstats.rowtabulates import rowTabulates

path = Path("/tmp/rowtabulates-seed1.bin")
subprocess.check_call(
    [
        "Rscript",
        "-e",
        "set.seed(1); n_row <- 2500L; n_col <- 800L; "
        "x <- matrix(sample.int(40L, n_row * n_col, replace = TRUE), nrow = n_row, ncol = n_col); "
        "x[sample.int(length(x), 5000L)] <- NA_integer_; "
        "writeBin(as.integer(x), '/tmp/rowtabulates-seed1.bin')",
    ]
)
flat = np.fromfile(path, dtype="<i4")
x = np.reshape(flat, (2500, 800), order="F")


def one():
    rowTabulates(x)


one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(statistics.median(elapsed))
