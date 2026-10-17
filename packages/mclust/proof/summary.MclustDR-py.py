import contextlib
import io
import statistics
import time

import numpy as np

from _mclust_dr_fit_fixture import PROOF, load_dr
from mclust.print_mclust_dr import print_summary_MclustDR, summary_MclustDR

dr = load_dr()


def one():
    return summary_MclustDR(dr)


def flat(s: dict) -> np.ndarray:
    return np.concatenate([
        np.asarray(s["n"], dtype=float),
        np.asarray([s["G"]], dtype=float),
        np.asarray(s["basis"], dtype=float).reshape(-1, order="F"),
        np.asarray(s["std.basis"], dtype=float).reshape(-1, order="F"),
        np.asarray(s["evalues"], dtype=float),
        np.asarray(s["evalues.cumperc"], dtype=float),
    ])


# untimed call: numeric values and printed text
s = one()
ref = np.loadtxt(PROOF / "summary.MclustDR-r-values.txt")
value = flat(s)
if value.shape != ref.shape:
    max_abs = float("inf")
else:
    max_abs = float(np.max(np.abs(value - ref)))
print(f"matches {'true' if max_abs <= 1e-8 else 'false'}")
print(f"max_abs_diff {max_abs:.17g}")

out = io.StringIO()
with contextlib.redirect_stdout(out):
    print_summary_MclustDR(s)
(PROOF.parent / "docs/output/summary.MclustDR-python.txt").write_text(out.getvalue())

# timed: median of 20 calls of summary() alone
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(f"translated_ms {statistics.median(elapsed):.17g}")
