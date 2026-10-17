"""Proof that plot.rq.process draws the Python-computed process."""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))

import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from plot_proof_common import (  # noqa: E402
    OUT,
    compare,
    new_figure,
    read_r_cases,
    time_median_ms,
)
from quantreg.plot import PlotLog, format_log, plot_rq_process  # noqa: E402
from quantreg.process import rq_fit_br_process  # noqa: E402

stem = "plot.rq.process"
data = np.loadtxt(PROOF.parent / "quantreg" / "data" / "check_design.txt")
X = data[:, :3]
y = data[:, 3]
obj = rq_fit_br_process(X, y)
obj["sol_names"] = ["tau", "Qbar", "Obj Fun", "(Intercept)", "x1", "x2"]


def case(nrow, ncol):
    def run(fig, log):
        plot_rq_process(obj, nrow=nrow, ncol=ncol, fig=fig, log=log)
    return run


cases = {
    "default_3x2": case(3, 2),
    "layout_2x2": case(2, 2),
}

out: list[str] = []
figure_case = "default_3x2"
for name, run in cases.items():
    fig = new_figure()
    log = PlotLog()
    run(fig, log)
    out.append(f"CASE {name}")
    out.extend(format_log(log))
    if name == figure_case:
        fig.savefig(OUT / f"{stem}-python.svg")
    plt.close(fig)
(OUT / f"{stem}-py.txt").write_text("\n".join(out) + "\n")

timed_fn = cases[figure_case]
ms = time_median_ms(new_figure, lambda fig: timed_fn(fig, None))

r_cases = read_r_cases(OUT / f"{stem}-r.txt")
py_cases = read_r_cases(OUT / f"{stem}-py.txt")
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
