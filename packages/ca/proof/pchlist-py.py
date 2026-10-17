"""Proof for pchlist (ca 0.72), Python side.

The translated pchlist_data is compared with the plot() call and the device
limits that pchlist-r.R recorded: the 256 point coordinates, the symbol codes
1:256, the plot-region limits (par("usr")), the default colour and cex, and the
frame (R calls box() once; matplotlib draws the frame as the axes spines).
Timing covers the data computation only, in the same form as the R side:
1000 computations per timed call, 1 untimed + 20 timed calls, reported per
computation.
"""

import sys
import time
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "packages/ca")
from ca.pchlist import pchlist, pchlist_data  # noqa: E402

OUT = Path("packages/ca/docs/output")
TOL = 1e-8
NAME = "pchlist"


def read_r(path):
    raw = {}
    for line in path.read_text().splitlines():
        parts = line.split("\t")
        raw[parts[0]] = parts[1:]
    return raw


RAW = read_r(OUT / f"{NAME}-r-values.txt")


def compare():
    data = pchlist_data()
    usr = [float(v) for v in RAW["plot.usr"]]
    fig, ax = plt.subplots(figsize=(7, 7))
    pchlist(ax)
    frame = 1 if all(ax.spines[s].get_visible() for s in ("left", "right", "top", "bottom")) else 0
    plt.close(fig)

    pairs = {
        "plot.x": (np.asarray(data["x"], float), "numeric"),
        "plot.y": (np.asarray(data["y"], float), "numeric"),
        "plot.pch": (np.asarray(data["pch"], float), "numeric"),
        "plot.usr": (np.array([*data["xlim"], *data["ylim"]], float), "numeric"),
        "plot.col": (data["col"][0], "text"),
        "plot.cex": (np.array([data["cex"][0]], float), "numeric"),
        "box.count": (np.array([frame], float), "numeric"),
    }
    report, failures = [], []
    max_diff = 0.0
    for key, (pv, kind) in pairs.items():
        rv = RAW[key]
        if kind == "text":
            if rv == [str(pv)]:
                report.append(key)
            else:
                failures.append(f"{key}: R {rv} vs Python {pv!r}")
            continue
        rf = np.array([float(v) for v in rv], float)
        if rf.shape != pv.shape:
            failures.append(f"{key}: length {rf.size} vs {pv.size}")
            continue
        d = float(np.max(np.abs(rf - pv)))
        max_diff = max(max_diff, d)
        if d <= TOL:
            report.append(key)
        else:
            failures.append(f"{key}: max diff {d}")
    # R's usr is the same as the limits we translate
    d_usr = float(np.max(np.abs(np.array(usr) - np.array([*data["xlim"], *data["ylim"]]))))
    max_diff = max(max_diff, d_usr)
    return report, failures, max_diff, data


def bench(fn, inner=1000, repeats=20):
    def block():
        for _ in range(inner):
            fn()

    block()
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        block()
        times.append((time.perf_counter() - start) * 1000.0 / inner)
    return float(np.median(times))


def draw_check():
    fig, ax = plt.subplots(figsize=(7, 7))
    pchlist(ax)
    fig.savefig(OUT / f"{NAME}.svg", format="svg")
    plt.close(fig)


def main():
    report, failures, max_diff, data = compare()
    draw_check()

    r_ms = float(read_r(OUT / f"{NAME}-r-ms.txt")["median_ms"][0])
    py_ms = bench(pchlist_data)
    (OUT / f"{NAME}-py-ms.txt").write_text(
        "function\tpchlist\n"
        f"median_ms\t{py_ms:.17g}\n"
        "timing\tpoints, symbol codes and limits that pchlist draws; 1000 computations "
        "per timed call, 1 untimed + 20 timed; reported per computation\n")
    speedup = r_ms / py_ms
    n_expected = 7
    matches = not failures and len(report) == n_expected
    lines = [
        "function\tpchlist",
        f"matches\t{'yes' if matches else 'no'}",
        f"tolerance\t{TOL}",
        f"compared_keys\t{len(report)} of {n_expected}",
        "compared_quantities\t256 point x and y coordinates, symbol codes 1:256, "
        "plot-region limits (par usr), default colour, cex, frame (box count)",
        f"max_abs_diff\t{max_diff:.3g}",
        f"r_ms\t{r_ms:.6g}",
        f"translated_ms\t{py_ms:.6g}",
        f"speedup\t{speedup:.4g}",
        "figure\tpchlist.svg",
    ]
    if failures:
        lines.append("failures\t" + " | ".join(failures))
    (OUT / f"{NAME}-compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
