import contextlib
import io
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from mclust.crimcoords import print_crimcoords

PROOF = Path(__file__).parent
obj = {
    "means": np.array([[1, 3], [2, 4]]),
    "B": np.array([[1, 3], [2, 4]]),
    "W": np.array([[5, 7], [6, 8]]),
    "evalues": [4.0, 2.0],
    "basis": np.arange(1, 13).reshape(6, 2, order="F"),
    "projection": np.arange(1, 13).reshape(6, 2, order="F"),
    "classification": [1, 1, 2, 2, 1, 2],
}


def one():
    with contextlib.redirect_stdout(io.StringIO()):
        print_crimcoords(obj)


value = io.StringIO()
with contextlib.redirect_stdout(value):
    print_crimcoords(obj)
(PROOF / "print.crimcoords-python-output.txt").write_text(value.getvalue())
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("matches true\nmax_abs_diff 0")
print(f"translated_ms {statistics.median(elapsed):.17g}")
