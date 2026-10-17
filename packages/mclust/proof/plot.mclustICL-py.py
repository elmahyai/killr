"""Python side of the plot.mclustICL proof.

Run from packages/mclust, after proof/plot.mclustICL-r.R:
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/plot.mclustICL-py.py

The ICL objects come from the translated mclustICL, so the proof also checks
its values against R's (the icl_values record, within 1e-8). The drawing log
is compared with R's trace log at 1e-8: the values, the window, each line and
the axis ticks. The timed call is the data computation of plot.mclustICL
(symbols, colours, model columns, y range, x values), not the drawing.
Figures go to docs/output/plot.mclustICL-<case>-python.svg.
"""

import matplotlib

matplotlib.use("Agg")

import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

PROOF = Path(__file__).resolve().parent
ROOT = PROOF.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PROOF))

from mclust._plot_common import Canvas  # noqa: E402
from mclust.mclust_icl import mclustICL  # noqa: E402
from mclust.plot_mclust_icl import plot_data, plot_mclustICL  # noqa: E402
from plot_fixtures import make_fixtures  # noqa: E402
from plot_trace import compare_logs, format_log, read_r_log  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)

OUT = ROOT / "docs" / "output"
MODELS6 = ["EII", "VII", "EEI", "VVI", "EEE", "VVV"]


def r_cases() -> dict[str, list[str]]:
    cases: dict[str, list[str]] = {}
    current = None
    for line in read_r_log(OUT / "plot.mclustICL-r.txt"):
        if line.startswith("CASE\t"):
            current = line.split("\t", 1)[1]
            cases[current] = []
        else:
            cases[current].append(line)
    return cases


def main() -> None:
    fx = make_fixtures()
    X2 = fx["data2"]
    X3 = fx["data3"]

    cases = [
        ("one_row_six_models", mclustICL(X2, G=[1], modelNames=MODELS6)),
        ("three_rows_six_models", mclustICL(X2, G=[1, 2, 3], modelNames=MODELS6)),
        ("three_rows_two_models_d3", mclustICL(X3, G=[1, 2, 3], modelNames=["EEE", "VVV"])),
        ("two_rows_subset_two_models", mclustICL(X2, G=[2, 3], modelNames=["VVV", "EII"])),
    ]

    reference = r_cases()
    overall = True
    worst = 0.0
    py_log: list[str] = []
    for name, obj in cases:
        canvas = Canvas()
        values = np.asarray(obj["values"], dtype=float)
        canvas.value("icl_values", values.ravel(order="F"))
        plot_mclustICL(obj, canvas=canvas)
        lines = format_log(canvas.log)
        res = compare_logs(reference[name], lines)
        overall = overall and res["matches"]
        worst = max(worst, res["max_abs_diff"])
        py_log.append(f"CASE\t{name}")
        py_log.extend(lines)
        print(f"case {name}: matches {'yes' if res['matches'] else 'no'} "
              f"entries {res['n_py']} max_abs_diff {res['max_abs_diff']:.3g}"
              + ("" if res["matches"] else f" first_mismatch {res['first_mismatch']}"))
    (OUT / "plot.mclustICL-py.txt").write_text("\n".join(py_log) + "\n")
    print(f"matches {'yes' if overall else 'no'}")
    print(f"max_abs_diff {worst:.17g}")

    for name, obj in cases:
        fig = Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        plot_mclustICL(obj, ax=ax)
        fig.savefig(OUT / f"plot.mclustICL-{name}-python.svg")

    three_rows = dict(cases)["three_rows_six_models"]

    def one() -> None:
        plot_data(three_rows)

    one()
    timed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        timed.append((time.perf_counter() - started) * 1000)
    t_ms = statistics.median(timed)
    (OUT / "plot.mclustICL-py-time.txt").write_text(f"{t_ms:.17g}\n")
    r_ms = float((OUT / "plot.mclustICL-r-time.txt").read_text())
    print(f"r_ms {r_ms:.17g}")
    print(f"translated_ms {t_ms:.17g}")
    print(f"speedup {r_ms / t_ms:.17g}")


if __name__ == "__main__":
    main()
