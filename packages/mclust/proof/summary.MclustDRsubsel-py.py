"""Python proof for summary.MclustDRsubsel, end to end from banknote, against R.

The subset fit is made outside the timed calls. Timing: one untimed call of the
summary, then the median of 20 calls. R side: summary.MclustDRsubsel-r.R.
"""

import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
PKG = PROOF.parent
sys.path.insert(0, str(PKG))

from mclust.mclust_dr import mclust_dr  # noqa: E402
from mclust.mclust_dr_subsel import MclustDRsubsel  # noqa: E402
from mclust.mclust_object import Mclust  # noqa: E402
from mclust.print_mclust_dr import _summary_text, summary_MclustDRsubsel  # noqa: E402

CASES = {
    "A": dict(g=[1, 2, 3], model_names=["VEI", "EEE"]),
    "B": dict(),
}


def read_banknote() -> np.ndarray:
    with (PROOF / "MclustDRsubsel_banknote4.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))[1:]
    return np.asarray([[float(v) for v in row] for row in rows], dtype=float)


def flatten(s: dict) -> np.ndarray:
    return np.concatenate([
        np.asarray(s["n"], dtype=float),
        np.asarray([s["G"]], dtype=float),
        np.asarray(s["basis"], dtype=float).reshape(-1, order="F"),
        np.asarray(s["std.basis"], dtype=float).reshape(-1, order="F"),
        np.asarray(s["evalues"], dtype=float),
        np.asarray(s["evalues.cumperc"], dtype=float),
    ])


def read_ref(path: Path) -> tuple[float, np.ndarray]:
    lines = path.read_text().splitlines()
    r_ms = float(lines[0].split()[1])
    return r_ms, np.asarray([float(x) for x in lines[1:]], dtype=float)


mod = Mclust(read_banknote(), G=3, modelNames="VEI")
dr = mclust_dr(mod, lambda_=0.7)
for case_id, kwargs in CASES.items():
    sub = MclustDRsubsel(dr, verbose=False, **kwargs)  # subset fit, outside timing

    def one():
        return summary_MclustDRsubsel(sub)

    s = one()  # untimed call
    value = flatten(s)
    r_ms, ref = read_ref(PROOF / f"summary.MclustDRsubsel-{case_id}-r-values.txt")
    max_abs = float("inf") if value.shape != ref.shape else float(np.max(np.abs(value - ref)))
    matches = max_abs <= 1e-8

    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000)
    translated_ms = statistics.median(elapsed)

    print(f"case {case_id}")
    print(f"matches {'true' if matches else 'false'}")
    print(f"max_abs_diff {max_abs:.17g}")
    print(f"r_ms {r_ms:.17g}")
    print(f"translated_ms {translated_ms:.17g}")
    print(f"speedup {r_ms / translated_ms:.17g}")

    if case_id == "A":
        (PROOF.parent / "docs" / "output" / "summary.MclustDRsubsel-python.txt").write_text(_summary_text(s))
