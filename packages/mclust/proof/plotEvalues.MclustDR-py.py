import matplotlib

matplotlib.use("Agg")

import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF.parent))
sys.path.insert(0, str(PROOF))

from matplotlib.figure import Figure  # noqa: E402

from _mclust_dr_fit_fixture import load_dr  # noqa: E402
from mclust.plot_mclust_dr import plotEvalues_MclustDR  # noqa: E402
from plot_trace import compare_logs, format_log, read_r_log  # noqa: E402

DOCS = PROOF.parent / "docs" / "output"
dr = load_dr()

r_cases: dict[str, list[str]] = {}
current = None
for line in read_r_log(PROOF / "plotEvalues.MclustDR-r-log.txt"):
    if line.startswith("#CASE\t"):
        current = line.split("\t", 1)[1]
        r_cases[current] = []
    else:
        r_cases[current].append(line)

cases = {
    "plot_true": dict(plot=True),
    "plot_false_numdir2": dict(plot=False, numdir=2),
}

overall = True
worst = 0.0
for name, kwargs in cases.items():
    canvas = plotEvalues_MclustDR(dr, **kwargs)
    res = compare_logs(r_cases[name], format_log(canvas.log))
    overall = overall and res["matches"]
    worst = max(worst, res["max_abs_diff"])
    print(f"case {name}: matches {'yes' if res['matches'] else 'no'} "
          f"entries {res['n_py']} max_abs_diff {res['max_abs_diff']:.3g}"
          + ("" if res["matches"] else f" first_mismatch {res['first_mismatch']}"))

fig = Figure(figsize=(6, 4))
plotEvalues_MclustDR(dr, plot=True, fig=fig)
fig.savefig(DOCS / "plotEvalues.MclustDR-python.svg")

print(f"matches {'yes' if overall else 'no'}")
print(f"max_abs_diff {worst:.17g}")

# Timing: the data computation only (plot = False).
plotEvalues_MclustDR(dr, plot=False)
timed = []
for _ in range(20):
    started = time.perf_counter()
    plotEvalues_MclustDR(dr, plot=False)
    timed.append((time.perf_counter() - started) * 1000)
r_ms = float((PROOF / "plotEvalues.MclustDR-r-ms.txt").read_text())
t_ms = statistics.median(timed)
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {t_ms:.17g}")
print(f"speedup {r_ms / t_ms:.17g}")
