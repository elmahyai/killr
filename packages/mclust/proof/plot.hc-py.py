"""Python side of the plot.hc proof. Same fixed cases and log format as plot.hc-r.R.

Compares the drawing log and the returned hclust values with R's log at 1e-8,
then times the data computation of plot.hc (as.hclust with the loglik, and the
dendrogram structure) with the median of 20 calls after one untimed call.
"""

import matplotlib

matplotlib.use("Agg")

import statistics  # noqa: E402
import warnings  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

PROOF = Path(__file__).resolve().parent
ROOT = PROOF.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PROOF))

from mclust._plot_common import Canvas  # noqa: E402
from mclust.plot_hc import as_dendrogram, as_hclust_loglik, plot_hc  # noqa: E402
from plot_trace import compare_logs, format_log, read_r_log  # noqa: E402

# mvn's Python port warns on singular covariances, as R's Fortran does silently.
warnings.filterwarnings("ignore", category=RuntimeWarning)

OUT = ROOT / "docs" / "output"
CASES = ["vvv_loglik", "vvv_merge", "eii_loglik"]


def load_case(name: str):
    pairs = np.loadtxt(PROOF / f"plot.hc_{name}_pairs.txt", ndmin=2)
    init = np.loadtxt(PROOF / f"plot.hc_{name}_init.txt", dtype=int, ndmin=1)
    data = np.loadtxt(PROOF / f"plot.hc_{name}_data.txt", ndmin=2)
    model, what = (PROOF / f"plot.hc_{name}_args.txt").read_text().split()
    hc_obj = {"pairs": pairs, "initialPartition": init, "data": data, "modelName": model}
    return hc_obj, what


def r_cases() -> dict[str, list[str]]:
    cases: dict[str, list[str]] = {}
    current = None
    for line in read_r_log(OUT / "plot.hc-r.txt"):
        if line.startswith("CASE\t"):
            current = line.split("\t", 1)[1]
            cases[current] = []
        else:
            cases[current].append(line)
    return cases


def run_case(name: str, ax=None):
    hc_obj, what = load_case(name)
    hier, usr, canvas = plot_hc(hc_obj, what=what, ax=ax)
    canvas.value("usr", usr)
    canvas.value("merge", np.asarray(hier["merge"]).ravel(order="F"))
    canvas.value("height", hier["height"])
    canvas.value("order", hier["order"])
    return hier, canvas


def main() -> None:
    reference = r_cases()
    overall = True
    worst = 0.0
    py_log: list[str] = []
    for name in CASES:
        _, canvas = run_case(name)
        lines = format_log(canvas.log)
        res = compare_logs(reference[name], lines)
        overall = overall and res["matches"]
        worst = max(worst, res["max_abs_diff"])
        py_log.append(f"CASE\t{name}")
        py_log.extend(lines)
        print(f"case {name}: matches {'yes' if res['matches'] else 'no'} "
              f"entries {res['n_py']} max_abs_diff {res['max_abs_diff']:.3g}"
              + ("" if res["matches"] else f" first_mismatch {res['first_mismatch']}"))
    (OUT / "plot.hc-py.txt").write_text("\n".join(py_log) + "\n")
    print(f"matches {'yes' if overall else 'no'}")
    print(f"max_abs_diff {worst:.17g}")

    for name in CASES:
        fig = Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        run_case(name, ax=ax)
        fig.savefig(OUT / f"plot.hc-{name}-python.svg")
        fig.savefig(OUT / f"plot.hc-{name}-python.png", dpi=110)

    hc_obj, _ = load_case("vvv_loglik")

    def one() -> None:
        as_dendrogram(as_hclust_loglik(hc_obj), hang=0)

    one()
    timed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        timed.append((time.perf_counter() - started) * 1000)
    t_ms = statistics.median(timed)
    (OUT / "plot.hc-py-time.txt").write_text(f"{t_ms:.17g}\n")
    r_ms = float((OUT / "plot.hc-r-time.txt").read_text())
    print(f"r_ms {r_ms:.17g}")
    print(f"translated_ms {t_ms:.17g}")
    print(f"speedup {r_ms / t_ms:.17g}")


if __name__ == "__main__":
    main()
