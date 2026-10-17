import matplotlib

matplotlib.use("Agg")

import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF.parent))
sys.path.insert(0, str(PROOF))

from matplotlib.figure import Figure  # noqa: E402

from mclust.dr_predict import crimcoords  # noqa: E402
from mclust.plot_crimcoords import plot_crimcoords  # noqa: E402
from plot_trace import compare_logs, format_log, read_r_log  # noqa: E402

DOCS = PROOF.parent / "docs" / "output"


def load(stem: str) -> np.ndarray:
    return np.loadtxt(PROOF / f"plot.crimcoords_{stem}.csv", delimiter=",", ndmin=2)


def labels(stem: str) -> list[str]:
    return [line for line in (PROOF / f"plot.crimcoords_{stem}.txt").read_text().splitlines() if line]


X3, X4 = load("X3"), load("X4")
cases = {
    "d2_three_classes": (X3, labels("cl3")),
    "pairs_d3_four_classes": (X4, labels("cl4")),
    "hist_numdir1_two_classes": (X4, labels("cl2")),
}

r_cases: dict[str, list[str]] = {}
current = None
for line in read_r_log(PROOF / "plot.crimcoords-r-log.txt"):
    if line.startswith("#CASE\t"):
        current = line.split("\t", 1)[1]
        r_cases[current] = []
    else:
        r_cases[current].append(line)

overall = True
worst = 0.0
for name, (X, cl) in cases.items():
    obj = crimcoords(X, cl)
    canvas = plot_crimcoords(obj)
    res = compare_logs(r_cases[name], format_log(canvas.log))
    overall = overall and res["matches"]
    worst = max(worst, res["max_abs_diff"])
    print(f"case {name} (numdir {obj['projection'].shape[1]}): matches "
          f"{'yes' if res['matches'] else 'no'} entries {res['n_py']} "
          f"max_abs_diff {res['max_abs_diff']:.3g}"
          + ("" if res["matches"] else f" first_mismatch {res['first_mismatch']}"))

print(f"matches {'yes' if overall else 'no'}")
print(f"max_abs_diff {worst:.17g}")

# Figures for the docs.
for name, (X, cl) in cases.items():
    fig = Figure(figsize=(6, 6))
    plot_crimcoords(crimcoords(X, cl), fig=fig)
    fig.savefig(DOCS / f"plot.crimcoords-{name}-python.svg")

# Timing: the data computation of the one-direction plot (pretty, the class
# split and the histogram densities). fig=None, so no drawing.
from mclust._plot_common import hist_density, nclass_sturges, pretty  # noqa: E402

obj1 = crimcoords(X4, labels("cl2"))


def one() -> None:
    proj = np.asarray(obj1["projection"])
    br = pretty(proj, nclass_sturges(proj))
    cls = np.asarray(obj1["classification"]).astype(str)
    for level in sorted(set(cls.tolist())):
        hist_density(proj[cls == level, 0], br)


one()
timed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    timed.append((time.perf_counter() - started) * 1000)
r_ms = float((PROOF / "plot.crimcoords-r-ms.txt").read_text())
t_ms = statistics.median(timed)
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {t_ms:.17g}")
print(f"speedup {r_ms / t_ms:.17g}")
