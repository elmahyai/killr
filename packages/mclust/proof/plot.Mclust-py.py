"""Python side of the plot.Mclust proof (one- and two-dimensional fits).

Reads the object JSON that plot_objects-r.R wrote and draws each panel with
the translated plot_Mclust. The log is compared with R's log at 1e-8. The
timed call is the density grid of the two-dimensional density panel (the data
computation), with no axes and no record. The d = 1 and d = 3 density panels
are compared as well (plotDensityMclust1 and plotDensityMclustd). The d = 3
cases draw the pairs grid of coordProj panels.
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

from mclust.plot_mclust import plot_Mclust  # noqa: E402

o2 = read_mclust_object(PROOF / "plot_object_mclust2d.json")
o1 = read_mclust_object(PROOF / "plot_object_mclust1d.json")
o3 = read_mclust_object(PROOF / "plot_object_mclust3d.json")


def _case(obj, what, **kw):
    def run(fig, ax, log):
        plot_Mclust(obj, what=what, ax=ax, log=log, **kw)
    return run


cases = {
    "all_default_2d": _case(o2, ("BIC", "classification", "uncertainty", "density")),
    "bic_2d": _case(o2, "BIC"),
    "classification_2d": _case(o2, "classification"),
    "classification_2d_no_ellipses": _case(o2, "classification", addEllipses=False),
    "uncertainty_2d": _case(o2, "uncertainty"),
    "density_2d": _case(o2, "density"),
    "classification_1d": _case(o1, "classification"),
    "uncertainty_1d": _case(o1, "uncertainty"),
    "classification_3d": _case(o3, "classification"),
    "classification_3d_no_ellipses": _case(o3, "classification", addEllipses=False),
    "uncertainty_3d": _case(o3, "uncertainty"),
    "density_1d": _case(o1, "density"),
    "density_3d": _case(o3, "density"),
}

stem = "plot.Mclust"
ms = run_proof(stem, cases, timed="density_2d")


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

# Figures of the Python drawing, for the docs.
import matplotlib.pyplot as plt  # noqa: E402

from mclust.plot_log import PlotLog  # noqa: E402

FIGS = {
    "bic_2d": (o2, "BIC", {}),
    "classification_2d": (o2, "classification", {}),
    "uncertainty_2d": (o2, "uncertainty", {}),
    "density_2d": (o2, "density", {}),
    "classification_1d": (o1, "classification", {}),
    "classification_3d": (o3, "classification", {}),
}
for name, (obj, what, kw) in FIGS.items():
    fig = plt.figure(figsize=(6, 6))
    plot_Mclust(obj, what=what, ax=fig.add_subplot(111), log=PlotLog(), **kw)
    fig.savefig(OUT / f"{stem}-{name}-python.svg")
    plt.close(fig)

r_ms = float((OUT / f"{stem}-r-time.txt").read_text())
print(f"matches {'yes' if overall else 'no'}")
print(f"max_abs_diff {worst:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {ms:.17g}")
print(f"speedup {r_ms / ms:.17g}")
