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

from _mclust_dr_fit_fixture import load_dr  # noqa: E402
from mclust.plot_mclust_dr import plot_MclustDR  # noqa: E402
from plot_trace import compare_logs, format_log, read_r_log  # noqa: E402

DOCS = PROOF.parent / "docs" / "output"

CASES = {
    "scatterplot": dict(what=("scatterplot",)),
    "pairs": dict(what=("pairs",)),
    "contour": dict(what=("contour",)),
    "classification": dict(what=("classification",)),
    "boundaries": dict(what=("boundaries",)),
    "density_dim1": dict(what=("density",), dimens=[1]),
    "evalues": dict(what=("evalues",)),
    "scatter_dims23": dict(what=("scatterplot",), dimens=[2, 3]),
    "default_all": dict(),
}

dr = load_dr()


def r_cases() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current = None
    for line in read_r_log(PROOF / "plot.MclustDR-r-log.txt"):
        if line.startswith("#CASE\t"):
            current = line.split("\t", 1)[1]
            out[current] = []
        else:
            out[current].append(line)
    return out


def run(name: str, fig=None):
    kwargs = dict(CASES[name])
    return plot_MclustDR(dr, fig=fig, **kwargs)


R = r_cases()
overall = True
worst = 0.0
for name in CASES:
    canvas = run(name)
    py_lines = format_log(canvas.log)
    res = compare_logs(R[name], py_lines)
    overall = overall and res["matches"]
    worst = max(worst, res["max_abs_diff"])
    print(f"case {name}: matches {'yes' if res['matches'] else 'no'} "
          f"entries {res['n_py']} max_abs_diff {res['max_abs_diff']:.3g}"
          + ("" if res["matches"] else f" first_mismatch {res['first_mismatch']}"))

print(f"matches {'yes' if overall else 'no'}")
print(f"max_abs_diff {worst:.17g}")

# Figures: one per panel type, drawn with the same data, as SVG for the docs.
for name in ("scatterplot", "pairs", "contour", "classification", "boundaries",
             "density_dim1", "evalues"):
    fig = Figure(figsize=(6, 6))
    run(name, fig=fig)
    fig.savefig(DOCS / f"plot.MclustDR-{name}-python.svg")

# Timing: median of 20 timed calls of the data computation (fig=None, so no drawing).
run("default_all")
timed = []
for _ in range(20):
    started = time.perf_counter()
    run("default_all")
    timed.append((time.perf_counter() - started) * 1000)
r_ms = float((PROOF / "plot.MclustDR-r-ms.txt").read_text())
t_ms = statistics.median(timed)
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {t_ms:.17g}")
print(f"speedup {r_ms / t_ms:.17g}")
