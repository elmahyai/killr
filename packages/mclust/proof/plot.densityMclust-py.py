"""Python side of the plot.densityMclust proof (one-dimensional fit).

The BIC, density (d = 1 and d = 2) and diagnostic panels are compared with R's log.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF.parent))
sys.path.insert(0, str(PROOF))

from plot_proof_common import OUT, run_proof  # noqa: E402  sets the Agg backend
from plot_object_io import read_mclust_object  # noqa: E402
from plot_compare import compare  # noqa: E402

from mclust.plot_density_mclust import plot_densityMclust  # noqa: E402

d1 = read_mclust_object(PROOF / "plot_object_density1d.json")
d2 = read_mclust_object(PROOF / "plot_object_density2d.json")


def _case(what, obj=None):
    def run(fig, ax, log):
        plot_densityMclust(d1 if obj is None else obj, what=what, ax=ax, log=log)
    return run


cases = {
    "bic_1d": _case(("BIC",)),
    "diagnostic_1d": _case(("diagnostic",)),
    "bic_and_diagnostic_1d": _case(("BIC", "diagnostic")),
    "density_1d": _case(("density",)),
    "density_2d": _case(("density",), d2),
}

stem = "plot.densityMclust"
ms = run_proof(stem, cases, timed="diagnostic_1d")


def read_cases(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current = None
    for line in path.read_text().splitlines():
        if line.startswith("CASE "):
            current = line[5:]
            out[current] = []
        elif line.strip() and current is not None:
            out[current].append(line)
    return out


r_cases = read_cases(OUT / f"{stem}-r.txt")
py_cases = read_cases(OUT / f"{stem}-py.txt")
overall = True
worst = 0.0
for name in cases:
    ok, diff, count, msg = compare(r_cases[name], py_cases[name])
    overall = overall and ok
    worst = max(worst, diff)
    print(f"case {name}: matches {'yes' if ok else 'no'} numbers {count} "
          f"max_abs_diff {diff:.3g}" + ("" if ok else f" first_mismatch {msg}"))

# Figures of the Python drawing, for the docs: BIC and diagnostic panels.
import matplotlib.pyplot as plt  # noqa: E402

from mclust.plot_log import PlotLog  # noqa: E402

fig, (ax_bic, ax_diag) = plt.subplots(1, 2, figsize=(10, 5))
plot_densityMclust(d1, what=("BIC",), ax=ax_bic, log=PlotLog())
plot_densityMclust(d1, what=("diagnostic",), ax=ax_diag, log=PlotLog())
fig.savefig(OUT / f"{stem}-bic-diagnostic-python.svg")
plt.close(fig)

r_ms = float((OUT / f"{stem}-r-time.txt").read_text())
print(f"matches {'yes' if overall else 'no'}")
print(f"max_abs_diff {worst:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {ms:.17g}")
print(f"speedup {r_ms / ms:.17g}")
