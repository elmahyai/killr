import matplotlib
matplotlib.use("Agg")

import statistics
import sys
import time
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

PROOF = Path(__file__).resolve().parent
ROOT = PROOF.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PROOF))

from mclust.mclust_ssc import mclust_ssc
from mclust.plot_log import PlotLog
from mclust.plot_mclust_ssc import plot_MclustSSC
from plot_trace import compare_logs, format_log, read_r_log

OUT = ROOT / "docs" / "output"


def load():
    x = np.loadtxt(PROOF / "MclustSSC_X.csv", delimiter=",", skiprows=1)
    import csv
    with (PROOF / "MclustSSC_class.csv").open(newline="") as f:
        cl = [float("nan") if r["class"] in ("", "NA") else r["class"]
              for r in csv.DictReader(f)]
    return mclust_ssc(x, cl, verbose=False)


def cases(mod):
    return {
        "classification": lambda fig, ax, log: plot_MclustSSC(
            mod, what="classification", addEllipses=False, ax=ax, log=log),
        "uncertainty": lambda fig, ax, log: plot_MclustSSC(
            mod, what="uncertainty", addEllipses=False, ax=ax, log=log),
    }


def main():
    mod = load()
    refs = {}
    current = None
    for line in read_r_log(OUT / "plot.MclustSSC-r.txt"):
        if line.startswith("CASE "):
            current = line.split(" ", 1)[1]
            refs[current] = []
        else:
            refs[current].append(line)
    out = []
    overall, worst = True, 0.0
    for name, case in cases(mod).items():
        log = PlotLog()
        fig = Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        case(fig, ax, log)
        lines = [line for line in format_log(log.log) if not line.startswith("U\t")]
        result = compare_logs(refs[name], lines)
        overall = overall and result["matches"]
        worst = max(worst, result["max_abs_diff"])
        out += [f"CASE {name}", *lines]
        fig.savefig(OUT / f"plot.MclustSSC-{name}-python.svg")
        print(name, "matches", result["matches"], "max_abs_diff", result["max_abs_diff"],
              result.get("first_mismatch"))
    (OUT / "plot.MclustSSC-py.txt").write_text("\n".join(out) + "\n")

    def one():
        plot_MclustSSC(mod, what="classification", log=PlotLog())
    one()
    times = []
    for _ in range(20):
        start = time.perf_counter()
        one()
        times.append((time.perf_counter() - start) * 1000)
    translated = statistics.median(times)
    r_ms = float((OUT / "plot.MclustSSC-r-time.txt").read_text())
    (OUT / "plot.MclustSSC-py-time.txt").write_text(f"{translated:.17g}\n")
    print("matches", "yes" if overall else "no")
    print("max_abs_diff", f"{worst:.17g}")
    print("r_ms", f"{r_ms:.17g}")
    print("translated_ms", f"{translated:.17g}")
    print("speedup", f"{r_ms / translated:.17g}")


if __name__ == "__main__":
    main()
