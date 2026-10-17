"""Python side of the plot.rqss proof.

Draws each case with quantreg.rqss_plot.plot_rqss and records the panel data
that plot_record.R records for quantreg's plot.rqss. The two logs are compared
at 1e-8, token by token. Band values are logged column-major, as R's as.numeric
writes a matrix. The timed call is the default case with the figure made outside
the timer.
"""

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
from quantreg.plot import PlotLog, format_log  # noqa: E402
from quantreg.rqss import rqss  # noqa: E402
from quantreg.rqss_plot import plot_rqss  # noqa: E402

stem = "plot.rqss"
n = 60
i = np.arange(1, n + 1, dtype=float)
x = 2 * np.sin(i)
z = np.cos(0.7 * i)
y = np.sin(x) + 0.5 * z + 0.3 * np.sin(7 * i)
data = {"y": y, "x": x, "z": z}

f2 = rqss("y ~ qss(x, lambda=2) + qss(z, lambda=1, Dorder=0)", data, tau=0.5)
g = rqss("y ~ qss(x, lambda=2) + qss(z, lambda=1)", data, tau=0.5)


def case(model, **kwargs):
    def run(fig, log):
        band = plot_rqss(model, fig=fig, log=log, **kwargs)
        if log is not None:
            for k, item in enumerate(band, start=1):
                if item is None:
                    continue
                log.record("V", [f"band{k}_x"], np.asarray(item["x"], dtype=float).ravel(order="F"))
                log.record("V", [f"band{k}_blo"], np.asarray(item["blo"], dtype=float).ravel(order="F"))
                log.record("V", [f"band{k}_bhi"], np.asarray(item["bhi"], dtype=float).ravel(order="F"))
    return run


cases = {
    "default_two_terms": case(f2),
    "pointwise_bands": case(g, bands="pointwise"),
    "both_bands_select2_titles": case(g, bands="both", select=[2], titles=["Effect A", "Effect B"]),
    "uniform_bands_pages1": case(g, bands="uniform", pages=1, coverage=0.9),
}

out: list[str] = []
figure_case = "pointwise_bands"
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

timed_model = f2
ms = time_median_ms(new_figure, lambda fig: plot_rqss(timed_model, fig=fig))

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
