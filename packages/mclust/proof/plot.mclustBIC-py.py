"""Python side of the plot.mclustBIC proof (G = 1 objects only).

The BIC objects come from the translated mclustBIC, so the proof also checks
that its values match R's (within 1e-8). The drawing log is compared with R's
trace log at 1e-8. The timed call is the data computation of plot.mclustBIC
(symbols, colours, model columns, y range, x values), not the drawing.
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
from mclust.bic_family import mclustBIC  # noqa: E402
from mclust.plot_mclust_bic import plot_data, plot_mclustBIC  # noqa: E402
from plot_fixtures import make_fixtures  # noqa: E402
from plot_trace import compare_logs, format_log, read_r_log  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)

OUT = ROOT / "docs" / "output"
MODELS6 = ["EII", "VII", "EEI", "VVI", "EEE", "VVV"]
MODELS3 = ["EII", "VVV", "EEE"]
SUBSET = ["VVV", "EII"]


def read_matrix(name: str) -> np.ndarray:
    rows = [line for line in (PROOF / f"plot.mclustBIC_{name}.txt").read_text().splitlines() if line]
    return np.array([[float(v) for v in row.split("\t")] for row in rows])


def r_cases() -> dict[str, list[str]]:
    cases: dict[str, list[str]] = {}
    current = None
    for line in read_r_log(OUT / "plot.mclustBIC-r.txt"):
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

    bic_a = mclustBIC(X2, G=1, modelNames=MODELS6)
    bic_b = mclustBIC(X3, G=1, modelNames=MODELS3)
    bic_c = mclustBIC(X2, G=1, modelNames=SUBSET)

    # Input check: the translated mclustBIC against R's BIC values.
    worst_bic = 0.0
    for name, obj in [("bic_a", bic_a), ("bic_b", bic_b), ("bic_c", bic_c)]:
        ref = read_matrix(name)
        py = np.atleast_2d(np.asarray(obj["values"], dtype=float))
        worst_bic = max(worst_bic, float(np.max(np.abs(py - ref))))
    print(f"mclustBIC values max_abs_diff {worst_bic:.17g}")

    reference = r_cases()
    cases = [
        ("six_models_d2", bic_a),
        ("three_models_d3", bic_b),
        ("subset_two_models_d2", bic_c),
    ]
    overall = True
    worst = 0.0
    py_log: list[str] = []
    for name, obj in cases:
        canvas = Canvas()
        plot_mclustBIC(obj, canvas=canvas)
        lines = format_log(canvas.log)
        res = compare_logs(reference[name], lines)
        overall = overall and res["matches"]
        worst = max(worst, res["max_abs_diff"])
        py_log.append(f"CASE\t{name}")
        py_log.extend(lines)
        print(f"case {name}: matches {'yes' if res['matches'] else 'no'} "
              f"entries {res['n_py']} max_abs_diff {res['max_abs_diff']:.3g}"
              + ("" if res["matches"] else f" first_mismatch {res['first_mismatch']}"))
    (OUT / "plot.mclustBIC-py.txt").write_text("\n".join(py_log) + "\n")
    print(f"matches {'yes' if overall else 'no'}")
    print(f"max_abs_diff {worst:.17g}")

    for name, obj in cases:
        fig = Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        plot_mclustBIC(obj, ax=ax)
        fig.savefig(OUT / f"plot.mclustBIC-{name}-python.svg")
        fig.savefig(OUT / f"plot.mclustBIC-{name}-python.png", dpi=110)

    def one() -> None:
        plot_data(bic_a)

    one()
    timed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        timed.append((time.perf_counter() - started) * 1000)
    t_ms = statistics.median(timed)
    (OUT / "plot.mclustBIC-py-time.txt").write_text(f"{t_ms:.17g}\n")
    r_ms = float((OUT / "plot.mclustBIC-r-time.txt").read_text())
    print(f"r_ms {r_ms:.17g}")
    print(f"translated_ms {t_ms:.17g}")
    print(f"speedup {r_ms / t_ms:.17g}")


if __name__ == "__main__":
    main()
