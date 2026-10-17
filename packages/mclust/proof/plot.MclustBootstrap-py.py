"""Proof: Python plot_MclustBootstrap (mclust.plot_mclust_bootstrap) against R mclust 6.1.3.

Run from packages/mclust, after proof/plot.MclustBootstrap-r.R:
    Rscript proof/plot.MclustBootstrap-r.R
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/plot.MclustBootstrap-py.py
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/plot.MclustBootstrap-compare.py

The bootstrap objects are read from docs/output/plot.MclustBootstrap-input.txt,
which the R proof wrote, so only the plot is under test. For each case, the
records (XLAB, HIST, USR, ABLINE, LINES, POINTS) are written in the R layout to
docs/output/plot.MclustBootstrap-py.txt.

Artist check: each case is also drawn on a Matplotlib figure (Agg). The axes
limits, bar edges and heights, the estimate line, the interval line and the
average marker are read back from the artists and compared with the records.
Results go to docs/output/plot.MclustBootstrap-artifacts.txt.

The median of 20 timed calls (time.perf_counter) of the timed case, after one
untimed call, is the last line as time_ms. The timed calls draw nothing, as R's
do in time mode.
"""

from __future__ import annotations

import math
import os
import statistics
import sys
import time
import warnings
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.simplefilter("ignore")

from mclust.plot_mclust_bootstrap import plot_MclustBootstrap  # noqa: E402

OUT = ROOT / "docs" / "output"


def read_inputs(path: Path) -> dict[str, dict]:
    """Rebuild the bootstrap objects from the R dump: prefix, key, dims, values."""
    objs: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        prefix, key, *rest = line.split("\t")
        obj = objs.setdefault(prefix, {"parameters": {}})
        if key in ("modelName", "type"):
            obj[key] = rest[0]
            continue
        dims = [int(v) for v in rest[0].split()]
        vals = rest[1].split() if len(rest) > 1 and rest[1] != "" else []
        arr = np.array([math.nan if v == "NA" else float(v) for v in vals], dtype=float)
        arr = arr.reshape(dims, order="F") if arr.size else arr.reshape(dims)
        if key.startswith("par_"):
            obj["parameters"][key[4:]] = arr
        elif key in ("G", "nboot", "nonfit"):
            obj[key] = int(arr.reshape(-1)[0])
        else:
            obj[key] = arr
    return objs


def fmt_num(v: float) -> str:
    if math.isnan(v):
        return "NA"
    return "%.17g" % v


def fmt_field(f) -> str:
    if isinstance(f, str):
        return f
    if isinstance(f, list) and all(isinstance(s, str) for s in f):
        return " ".join(f)
    arr = np.asarray(f, dtype=float).ravel()
    return " ".join(fmt_num(v) for v in arr)


def record_lines(panels) -> list[str]:
    lines = []
    for p in panels:
        for tag, fields in p["records"]:
            lines.append("\t".join([tag] + [fmt_field(f) for f in fields]))
    return lines


# varnames: R's rownames(parameters$mean). R's Mclust names the columns "xb1",
# "xb2" (deparsed data name); the Python Mclust object keeps no dimnames, so the
# names are passed in. pb_mean_nonames has no names, as in the R case.
NAMES = ("xb1", "xb2")
CASES = {
    "bs_pro_default": dict(obj="bs", what="pro"),
    "bs_mean_noint": dict(obj="bs", what="mean", show_parest=False, show_confint=False,
                          varnames=NAMES),
    "bs_var_custom": dict(obj="bs", what="var", xlim=(0.0, 0.6), breaks=6,
                          xlab="sd of var", col="red", lwd=1, lty=2,
                          hist_col="lightblue", hist_border="black", varnames=NAMES),
    "jk_mean_default": dict(obj="jk", what="mean", varnames=NAMES),
    "pb_pro_scalarbreaks": dict(obj="pb", what="pro", breaks=12),
    "pb_mean_nonames": dict(obj="pb", what="mean"),
    "bs_pro_ylim": dict(obj="bs", what="pro", ylim=(0.0, 100.0), show_confint=False, xlab="p"),
}


def run_case(objs, spec, fig=None):
    kw = {k: v for k, v in spec.items() if k != "obj"}
    return plot_MclustBootstrap(objs[spec["obj"]], fig=fig, **kw)


def timed_call(objs):
    # R's timed case: three plot calls with the defaults, no figure.
    b = objs["bs"]
    plot_MclustBootstrap(b, what="pro")
    plot_MclustBootstrap(b, what="mean")
    plot_MclustBootstrap(b, what="var")


def artifact_check(fig, panels, spec) -> dict:
    """Read the drawn artists back and compare them with the records."""
    max_diff = 0.0
    problems: list[str] = []
    axes = fig.axes
    if len(axes) != len(panels):
        problems.append(f"axes {len(axes)} != panels {len(panels)}")
    for ax, p in zip(axes, panels):
        rec = dict(p["records"])
        usr = p["usr"]
        xl, yl = ax.get_xlim(), ax.get_ylim()
        d = max(abs(xl[0] - usr[0]), abs(xl[1] - usr[1]), abs(yl[0] - usr[2]), abs(yl[1] - usr[3]))
        max_diff = max(max_diff, d)
        if d > 1e-8:
            problems.append(f"usr {xl} {yl} vs {usr}")
        if ax.get_xlabel() != p["lab"]:
            problems.append(f"xlabel {ax.get_xlabel()!r} vs {p['lab']!r}")
        breaks = p["hist"]["breaks"]
        y = p["hist"]["y"]
        bars = ax.patches
        lefts = np.array([b.get_x() for b in bars])
        heights = np.array([b.get_height() for b in bars])
        if bars:
            edges = np.append(lefts, lefts[-1] + bars[-1].get_width())
            d = max(np.max(np.abs(edges - breaks)), np.max(np.abs(heights - y)))
            max_diff = max(max_diff, float(d))
            if d > 1e-8:
                problems.append("bar edges or heights differ")
        lines = ax.lines
        k = 0
        if spec.get("show_parest", True):
            xs = np.asarray(lines[k].get_xdata(), dtype=float)
            d = float(np.max(np.abs(xs - p["stat"])))
            max_diff = max(max_diff, d)
            k += 1
        if spec.get("show_confint", True):
            ln = lines[k]
            xs = np.asarray(ln.get_xdata(), dtype=float)
            ys = np.asarray(ln.get_ydata(), dtype=float)
            d = max(float(np.max(np.abs(xs - p["ci"]))), float(np.max(np.abs(ys - p["y0"]))))
            max_diff = max(max_diff, d)
            off = ax.collections[0].get_offsets()
            d2 = max(abs(float(off[0][0]) - p["ave"]), abs(float(off[0][1]) - p["y0"]))
            max_diff = max(max_diff, d2)
        if "ABLINE" in rec and not spec.get("show_parest", True):
            problems.append("ABLINE recorded without show_parest")
    return {"max_diff": max_diff, "problems": problems}


def main() -> int:
    objs = read_inputs(OUT / "plot.MclustBootstrap-input.txt")
    out: list[str] = []
    artifact_lines: list[str] = []
    svg_done = set()
    for name, spec in CASES.items():
        fig = plt.figure(figsize=(9, 6))
        panels = run_case(objs, spec, fig=fig)
        out.append(f"CASE {name}")
        out.extend(record_lines(panels))
        res = artifact_check(fig, panels, {"show_parest": spec.get("show_parest", True),
                                           "show_confint": spec.get("show_confint", True)})
        artifact_lines.append(
            f"{name}: panels={len(panels)} artist_max_abs_diff={res['max_diff']:.3g} "
            f"problems={len(res['problems'])}")
        for p in res["problems"][:5]:
            artifact_lines.append(f"  problem: {p}")
        if name in ("bs_pro_default", "jk_mean_default") and name not in svg_done:
            OUT.mkdir(parents=True, exist_ok=True)
            fig.savefig(OUT / f"plot.MclustBootstrap-{name}-python.svg")
            svg_done.add(name)
        plt.close(fig)

    timed_call(objs)
    times = []
    for _ in range(20):
        started = time.perf_counter()
        timed_call(objs)
        times.append((time.perf_counter() - started) * 1000.0)
    out.append(f"time_ms\t{'%.17g' % statistics.median(times)}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plot.MclustBootstrap-py.txt").write_text("\n".join(out) + "\n")
    (OUT / "plot.MclustBootstrap-artifacts.txt").write_text("\n".join(artifact_lines) + "\n")
    print("\n".join(artifact_lines))
    print("Python plot.MclustBootstrap median ms:", statistics.median(times))
    return 0


if __name__ == "__main__":
    sys.exit(main())
