"""Proof for lmom::evdistq against R lmom 3.3.

Runs the real R evdistq (``evdistq-r.R``) and the Python port on the cases in
``evdistq_cases.json``. For every case the proof compares, within 1e-8:

* the grid (reduced variates) and the curve that evdistq returns, against the
  x and y that R's lines() receives;
* the curve as drawn: the x and y of the Matplotlib line, read back from the axes;
* the plot-region limits (R's ``par("usr")``) against the Matplotlib axis limits;
* the line colour, type and width.

The figure case is drawn in R to an SVG and in Python with Matplotlib. Their data
is compared; the SVG files are kept as the examples.

Timing covers the data step: R's evdistq with lines() as a no-op, and Python's
``evdistq_data``. One untimed call, then the median of 20 timed calls. speedup is
R time divided by Python time.
"""

from __future__ import annotations

import importlib
import json
import statistics
import subprocess
import sys
import time
import types
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_hex  # noqa: E402

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
ROOT = HERE.parents[2]
OUT = PKG / "docs" / "output"
sys.path.insert(0, str(PKG))

from lmom._plotting import LINESTYLE_TO_LTY, extend_range  # noqa: E402
from lmom.evdistq import evdistq, evdistq_data  # noqa: E402

TOL = 1e-8
CASES = HERE / "evdistq_cases.json"
R_SCRIPT = HERE / "evdistq-r.R"
R_VALUES = OUT / "evdistq_r_values.txt"
R_TIME = OUT / "evdistq_r_time.txt"
R_FIG = OUT / "evdistq_r_example.svg"
PY_VALUES = OUT / "evdistq_python_values.txt"
PY_FIG = OUT / "evdistq_example.svg"
PROOF = OUT / "evdistq_proof.txt"

NUMERIC_FIELDS = ("usr", "x", "y", "drawn_x", "drawn_y", "lwd")
STRING_FIELDS = ("col", "lty")


# ---------------------------------------------------------------- record format
def _num(text: str) -> float:
    return float("nan") if text == "NA" else float(text)


def read_records(path: Path) -> tuple[list[str], dict[str, list[dict]]]:
    order: list[str] = []
    recs: dict[str, list[dict]] = {}
    cur = None
    for raw in path.read_text().splitlines():
        parts = raw.split("\t")
        if parts[0] == "#case":
            cur = parts[1]
            order.append(cur)
            recs[cur] = []
        elif parts[0] == "@record":
            recs[cur].append({})
        else:
            field, kind, vals = parts[0], parts[1], parts[2:]
            recs[cur][-1][field] = vals if kind == "s" else [_num(v) for v in vals]
    return order, recs


def write_records(path: Path, order: list[str], recs: dict[str, list[dict]]) -> None:
    lines = []
    for name in order:
        lines.append(f"#case\t{name}")
        for rec in recs[name]:
            lines.append("@record\tlines")
            for field in ("usr", "x", "y", "drawn_x", "drawn_y"):
                text = ["NA" if np.isnan(v) else f"{v:.17g}" for v in rec[field]]
                lines.append("\t".join([field, "n", *text]))
            lines.append("\t".join(["col", "s", rec["col"]]))
            lines.append("\t".join(["lty", "s", rec["lty"]]))
            lines.append("\t".join(["lwd", "n", f"{rec['lwd']:.17g}"]))
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------- inputs
def flat_quantile(name: str):
    """lmom's quantile functions sit in packages/lmom, outside the lmom package folder."""
    if "lmom_flat" not in sys.modules:
        flat = types.ModuleType("lmom_flat")
        flat.__path__ = [str(PKG)]
        sys.modules["lmom_flat"] = flat
    return getattr(importlib.import_module(f"lmom_flat.{name}"), name)


def usr_of(case: dict) -> tuple[list[float], list[float]]:
    """R's par("usr") after plot.window: the limits, widened by 4 percent when xaxs or yaxs is "r"."""
    xlim = [float(v) for v in case["xlim"]]
    ylim = [float(v) for v in case.get("ylim", [0, 1])]
    if case.get("xaxs", "r") == "r":
        xlim = list(extend_range(*xlim))
    if case.get("yaxs", "r") == "r":
        ylim = list(extend_range(*ylim))
    return xlim, ylim


def draw_case(case: dict, ax):
    """Set the plot region as R does, then call the Python evdistq on the axes."""
    xlim, ylim = usr_of(case)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    qfunc = flat_quantile(case["qfunc"])
    para = case.get("para")
    para = None if para is None else np.asarray(para, dtype=float)
    kwargs = {k: case[k] for k in ("col", "lty", "lwd") if k in case}
    xval, yval = evdistq(qfunc, para, int(case["npoints"]), ax=ax, **kwargs)
    return xval, yval


def python_record(case: dict) -> dict:
    fig, ax = plt.subplots(figsize=(7, 7))
    xval, yval = draw_case(case, ax)
    line = ax.get_lines()[-1]
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    rec = {
        "usr": np.array([*xlim, *ylim], dtype=float),
        "x": np.asarray(xval, dtype=float),
        "y": np.asarray(yval, dtype=float),
        "drawn_x": np.asarray(line.get_xdata(), dtype=float),
        "drawn_y": np.asarray(line.get_ydata(), dtype=float),
        "col": to_hex(line.get_color()),
        "lty": LINESTYLE_TO_LTY[line.get_linestyle()],
        "lwd": float(line.get_linewidth()),
    }
    plt.close(fig)
    return rec


# ---------------------------------------------------------------- compare
def _max_diff(a: np.ndarray, b: np.ndarray) -> float | None:
    """Largest abs difference over finite values. None when the shapes or the non-finite positions differ."""
    if a.shape != b.shape:
        return None
    if not np.array_equal(np.isnan(a), np.isnan(b)):
        return None
    if not np.array_equal(np.isposinf(a), np.isposinf(b)) or not np.array_equal(np.isneginf(a), np.isneginf(b)):
        return None
    fin = np.isfinite(a) & np.isfinite(b)
    return float(np.max(np.abs(a[fin] - b[fin]))) if fin.any() else 0.0


def compare(order, r_recs, p_recs) -> dict:
    mismatches: list[str] = []
    max_abs = 0.0
    fields = 0
    for name in order:
        r = r_recs[name]
        p = p_recs[name][0]
        if len(r) != 1:
            mismatches.append(f"{name}: R logged {len(r)} lines() calls, expected 1")
            continue
        r = r[0]
        # R's lines() x and y against the returned grid/curve and the drawn line.
        pairs = {
            "usr": (r["usr"], p["usr"]),
            "x": (r["x"], p["x"]),
            "y": (r["y"], p["y"]),
            "drawn_x": (r["x"], p["drawn_x"]),
            "drawn_y": (r["y"], p["drawn_y"]),
            "lwd": (r["lwd"], [p["lwd"]]),
        }
        for field in NUMERIC_FIELDS:
            a = np.asarray(pairs[field][0], dtype=float)
            b = np.asarray(pairs[field][1], dtype=float)
            d = _max_diff(a, b)
            fields += 1
            if d is None:
                mismatches.append(f"{name} {field}: R {a.size} values, Python {b.size}, or non-finite positions differ")
            else:
                max_abs = max(max_abs, d)
                if d > TOL:
                    mismatches.append(f"{name} {field}: max abs diff {d:.3e}")
        if to_hex(r["col"][0]) != to_hex(p["col"]):
            mismatches.append(f"{name} col: R {r['col'][0]} Python {p['col']}")
        if r["lty"][0] != p["lty"]:
            mismatches.append(f"{name} lty: R {r['lty'][0]} Python {p['lty']}")
        fields += 2
    return {"cases": len(order), "fields": fields, "max_abs_diff": max_abs, "mismatches": mismatches}


# ---------------------------------------------------------------- timing
def median_seconds(fn) -> float:
    fn()
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return statistics.median(times)


# ---------------------------------------------------------------- main
def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["Rscript", "--slave", str(R_SCRIPT), str(CASES), str(R_VALUES),
                    str(R_TIME), str(R_FIG)], cwd=ROOT, check=True)

    cases = json.loads(CASES.read_text())["cases"]
    order, r_recs = read_records(R_VALUES)
    by_name = {c["name"]: c for c in cases}
    p_recs = {name: [python_record(by_name[name])] for name in order}
    write_records(PY_VALUES, order, p_recs)

    # Figure: the same case, drawn in Matplotlib and saved as the example.
    fig_case = next(c for c in cases if c.get("figure"))
    fig, ax = plt.subplots(figsize=(7, 7))
    draw_case(fig_case, ax)
    fig.savefig(PY_FIG, format="svg")
    plt.close(fig)

    report = compare(order, r_recs, p_recs)

    prim = next(c for c in cases if c.get("primary"))
    xlim, _ = usr_of(prim)
    para = np.asarray(prim["para"], dtype=float)
    py_s = median_seconds(lambda: evdistq_data(flat_quantile(prim["qfunc"]), para,
                                               int(prim["npoints"]), xlim))
    r_s = float(R_TIME.read_text())

    matches = not report["mismatches"] and report["max_abs_diff"] <= TOL
    lines = [
        "function: evdistq",
        f"matches: {'yes' if matches else 'no'}",
        f"cases: {report['cases']}",
        f"fields_compared: {report['fields']}",
        f"max_abs_diff: {report['max_abs_diff']:.3e}",
        f"tolerance: {TOL:g}",
        f"timed_case: {prim['name']}",
        f"r_ms: {r_s * 1000:.6g}",
        f"translated_ms: {py_s * 1000:.6g}",
        f"speedup: {r_s / py_s:.4g}",
        f"r_figure: {R_FIG.relative_to(ROOT)}",
        f"python_figure: {PY_FIG.relative_to(ROOT)}",
    ]
    if report["mismatches"]:
        lines.append("mismatches:")
        lines.extend(f"  {m}" for m in report["mismatches"])
    PROOF.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
