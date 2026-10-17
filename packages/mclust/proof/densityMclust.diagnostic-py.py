"""Python side of the densityMclust.diagnostic proof (one-dimensional fit).

Reads the object JSON that plot_objects-r.R wrote, draws it with the
translated densityMclust_diagnostic, and compares the log with R's log.
The timed call is the data computation (the CDF grid, the quantiles and
the QQ line) with no axes and no record.
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

from mclust.density_mclust_diagnostic import densityMclust_diagnostic  # noqa: E402
from mclust.plot_log import PlotLog  # noqa: E402

d1 = read_mclust_object(PROOF / "plot_object_density1d.json")
d2 = read_mclust_object(PROOF / "plot_object_density2d.json")


def _case(type_=("cdf", "qq"), obj=d1):
    def run(fig, ax, log):
        densityMclust_diagnostic(obj, type=type_, ax=ax, log=log)
    return run


cases = {
    "cdf_qq_1d": _case(),
    "cdf_only_1d": _case(("cdf",)),
    "qq_only_1d": _case(("qq",)),
    "multivariate_no_draw": _case(obj=d2),
}

stem = "densityMclust.diagnostic"
ms = run_proof(stem, cases, timed="cdf_qq_1d")


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

# Figures of the Python drawing: the CDF diagnostic and the QQ diagnostic.
import matplotlib.pyplot as plt  # noqa: E402

from mclust.plot_log import PlotLog  # noqa: E402

fig, (ax_cdf, ax_qq) = plt.subplots(1, 2, figsize=(10, 5))
densityMclust_diagnostic(d1, type=("cdf",), ax=ax_cdf, log=PlotLog())
densityMclust_diagnostic(d1, type=("qq",), ax=ax_qq, log=PlotLog())
fig.savefig(OUT / f"{stem}-cdf-qq-python.svg")
plt.close(fig)

r_ms = float((OUT / f"{stem}-r-time.txt").read_text())
print(f"matches {'yes' if overall else 'no'}")
print(f"max_abs_diff {worst:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {ms:.17g}")
print(f"speedup {r_ms / ms:.17g}")
