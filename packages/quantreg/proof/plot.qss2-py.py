"""Python side of the plot.qss2 proof.

Draws each case with quantreg.rqss_plot.plot_qss2 and records the plot values that
plot.qss2-r.R records for quantreg's plot.qss2: the labels and window, the points
plotted with type "n", the interp grid that is contoured (with NA as 0 and an NA
indicator), and the convex hull returned. The two logs are compared at 1e-8, token by
token. The contour lines are Matplotlib's and are not compared; see the gap note in
plot_qss2. The timed call is the default case with the figure made outside the timer.
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
# interp is loaded from its Python package in packages/interp, as the tri.find proofs do.
sys.path.insert(0, str(PROOF.parents[1] / "interp"))

import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from plot_proof_common import (  # noqa: E402
    OUT,
    compare,
    new_figure,
    read_r_cases,
    time_median_ms,
)
from quantreg.plot import PlotLog, format_log  # noqa: E402
from quantreg.rqss_plot import plot_qss2  # noqa: E402

stem = "plot.qss2"
ROOT = PROOF.parent

d = np.loadtxt(ROOT / "quantreg" / "data" / "check_design.txt")
X = np.column_stack([d[:, 1], d[:, 2]])
px = X[:, 0]
py = X[:, 1]
pz = np.sin(2 * px) + py**2 - 0.5 * px * py
xyz = np.column_stack([px, py, pz])
xyz_subset = xyz[:25, :]
xyz_shifted = np.column_stack([px, py, pz + 2])


def case(data, **kwargs):
    def run():
        fig = new_figure()
        log = PlotLog()
        try:
            plot_qss2(data, fig=fig, log=log, **kwargs)
            lines = format_log(log)
        except ValueError as err:
            lines = [f"ERR {err}"]
        return fig, lines

    return run


cases = {
    "contour_default": case(xyz),
    "contour_subset25": case(xyz_subset),
    "contour_shifted_z": case(xyz_shifted),
    "render_unknown": case(xyz, render="bogus"),
}

out: list[str] = []
for name, run in cases.items():
    fig, lines = run()
    out.append(f"CASE {name}")
    out.extend(lines)
    if name == "contour_default":
        fig.savefig(OUT / f"{stem}-python.svg")
    plt.close(fig)
(OUT / f"{stem}-python.txt").write_text("\n".join(out) + "\n")

ms = time_median_ms(new_figure, lambda fig: plot_qss2(xyz, fig=fig))

r_cases = read_r_cases(OUT / f"{stem}-r.txt")
py_cases = read_r_cases(OUT / f"{stem}-python.txt")
overall = True
worst = 0.0
for name in cases:
    ok, diff, count, msg = compare(r_cases[name], py_cases[name])
    overall = overall and ok
    worst = max(worst, diff)
    print(
        f"case {name}: matches {'yes' if ok else 'no'} numbers {count} "
        f"max_abs_diff {diff:.3g}" + ("" if ok else f" first_mismatch {msg}")
    )

r_ms = float((OUT / f"{stem}-r-time.txt").read_text())
print(f"matches {'yes' if overall else 'no'}")
print(f"max_abs_diff {worst:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {ms:.17g}")
print(f"speedup {r_ms / ms:.17g}")
