"""Python side of the plot.rqs proof.

Draws each case with quantreg.plot.plot_rqs and records the same panel data
that plot_record.R records for quantreg's plot.rqs. The two logs are compared
at 1e-8. The timed call is the default case with the figure made outside the timer.
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))

from plot_proof_common import (  # noqa: E402
    OUT,
    compare,
    new_figure,
    read_r_cases,
    time_median_ms,
)

import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from quantreg import rq  # noqa: E402
from quantreg.plot import PlotLog, format_log, plot_rqs  # noqa: E402

stem = "plot.rqs"
A = np.loadtxt(PROOF.parent / "quantreg" / "data" / "check_design.txt")
X = A[:, :3]
y = A[:, 3]
data = {"y": y, "x1": X[:, 1], "x2": X[:, 2]}
fit = rq("y ~ x1 + x2", tau=[0.25, 0.5, 0.75], data=data)


def case(**kwargs):
    def run(fig, log):
        value = plot_rqs(fit, fig=fig, log=log, **kwargs)
        if log is not None:
            arr = np.asarray(value, dtype=float)
            log.record("V", ["ret"], arr.ravel(order="F"))
    return run


cases = {
    "all_default_ols": case(),
    "no_ols": case(ols=False),
    "parm_x1_ols": case(parm=["x1"]),
    "fixed_ylim_ols": case(ylim=[-1.5, 1.5]),
}

out: list[str] = []
figure_case = "all_default_ols"
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
