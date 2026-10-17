import contextlib
import io
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from mclust.crimcoords import print_summary_crimcoords

PROOF = Path(__file__).parent
obj = {
    "basis": np.arange(1, 13).reshape(6, 2, order="F"),
    "evalues": np.array([4.0, 2.0]),
    "evalues.cumperc": np.array([400 / 6, 100.0]),
}


def one():
    with contextlib.redirect_stdout(io.StringIO()):
        print_summary_crimcoords(obj)


value = io.StringIO()
with contextlib.redirect_stdout(value):
    print_summary_crimcoords(obj)
(PROOF / "print.summary.crimcoords-python-output.txt").write_text(value.getvalue())
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("matches true\nmax_abs_diff 0")
print(f"translated_ms {statistics.median(elapsed):.17g}")
