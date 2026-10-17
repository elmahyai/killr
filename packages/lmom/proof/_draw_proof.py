"""Shared proof for the drawing functions of lmom (lmrd, lmrdpoints, lmrdlines, evplot,
evplot.default, evpoints).

What is compared, for every case in ``draw_cases.json``:

* each drawing record R makes (curve lines, points, two-parameter text, legend,
  plot, lines, axis ticks, return-period title, the returned ``out`` list) against
  the same record read back from the Matplotlib artists the Python function
  created. Numbers must agree within 1e-8; labels and colours must be equal.
* the plot-region limits after the call (R's ``par("usr")``) against the
  Matplotlib axis limits.
* the error message when R stops, against the Python error.

Timing covers the data step only: R runs the real function with the drawing
primitives turned into no-ops, and Python runs the ``*_plan`` or ``*_data``
function. One untimed call, then the median of 20 timed calls.
"""

from __future__ import annotations

import importlib
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
sys.path.insert(0, str(ROOT))

TOL = 1e-8
_NAN = float("nan")

# Fields that depend on the device height, not on the data. They are reported, not compared.
IGNORED = {
    "lmrd": {("legend", "y")},
    "lmrdpoints": set(),
    "lmrdlines": set(),
    "evplot": {("text", "y")},
    "evplot.default": {("text", "y")},
    "evpoints": set(),
}
COLOUR_FIELDS = {"col", "col_lines", "col_pts"}


# ---------------------------------------------------------------- record format
def write_records(path: Path, cases: list[tuple[str, list]]) -> None:
    lines = []
    for name, records in cases:
        lines.append(f"#case\t{name}")
        for fn, fields in records:
            lines.append(f"@record\t{fn}")
            for field, (kind, value) in fields.items():
                if kind == "s":
                    lines.append("\t".join([field, "s", *value]))
                else:
                    text = ["NA" if np.isnan(v) else f"{v:.17g}" for v in value]
                    lines.append("\t".join([field, "n", *text]))
    path.write_text("\n".join(lines) + "\n")


def read_records(path: Path) -> list[tuple[str, list]]:
    cases: list[tuple[str, list]] = []
    for raw in path.read_text().splitlines():
        parts = raw.split("\t")
        if parts[0] == "#case":
            cases.append((parts[1], []))
        elif parts[0] == "@record":
            cases[-1][1].append((parts[1], {}))
        else:
            field, kind, values = parts[0], parts[1], parts[2:]
            if kind == "s":
                cases[-1][1][-1][1][field] = ("s", values)
            else:
                nums = [_NAN if v == "NA" else float(v) for v in values]
                cases[-1][1][-1][1][field] = ("n", nums)
    return cases


def N(values) -> tuple:
    return ("n", [_NAN if v is None else float(v) for v in np.atleast_1d(values)])


def S(values) -> tuple:
    return ("s", [str(v) for v in values])


# ---------------------------------------------------------------- inputs
def flat_quantile(name: str):
    """lmom's quantile functions sit in packages/lmom, outside the lmom package folder."""
    if "lmom_flat" not in sys.modules:
        flat = types.ModuleType("lmom_flat")
        flat.__path__ = [str(PKG)]
        sys.modules["lmom_flat"] = flat
    return getattr(importlib.import_module(f"lmom_flat.{name}"), name)


def to_python_args(args: dict) -> dict:
    out = {}
    for key, value in args.items():
        py = key.replace(".", "_")
        if key == "qfunc":
            out[py] = flat_quantile(value)
        elif isinstance(value, dict):
            out[py] = dict(value)
        elif isinstance(value, list):
            out[py] = np.array([np.nan if v is None else v for v in value], dtype=float)
        else:
            out[py] = value
    return out


def load_cases(group: str) -> list[dict]:
    import json

    return json.loads((HERE / "draw_cases.json").read_text())[group]


def group_of(fname: str) -> str:
    return "evplot" if fname in ("evplot", "evplot.default") else fname


# ---------------------------------------------------------------- artist readers
def _pch_of(line) -> int:
    from lmom._plotting import _MARKER_TO_PCH

    marker = line.get_marker()
    if marker in (None, "", "None"):
        return 1
    filled = line.get_markerfacecolor() not in ("none", None)
    return _MARKER_TO_PCH.get((marker, filled), -1)


def _type_of(line) -> str:
    has_line = line.get_linestyle() not in ("None", "none", "", None)
    has_marker = line.get_marker() not in (None, "", "None")
    if has_line and has_marker:
        return "b"
    if has_line:
        return "l"
    return "p"


def _lty_of(line) -> str:
    from lmom._plotting import LINESTYLE_TO_LTY

    return LINESTYLE_TO_LTY[line.get_linestyle()]


def _line_by_label(ax, label):
    return [ln for ln in ax.get_lines() if ln.get_label() == label]


def _texts_by_label(ax, label):
    return [t for t in ax.texts if t.get_label() == label]


def _usr(ax) -> list[float]:
    return [*ax.get_xlim(), *ax.get_ylim()]


# ---------------------------------------------------------------- python runners
def run_lmrd(args: dict, ax):
    from lmom.lmrd import lmrd

    out = lmrd(ax=ax, **args)
    recs = []
    for ln in ax.get_lines():
        if ln.get_label().startswith("curve:"):
            recs.append(("curve", {
                "x": N(ln.get_xdata()), "y": N(ln.get_ydata()),
                "col": S([ln.get_color()]), "lty": S([_lty_of(ln)]),
                "lwd": N([ln.get_linewidth()]),
            }))
    for ln in _line_by_label(ax, "twopar"):
        recs.append(("points", {
            "x": N(ln.get_xdata()), "y": N(ln.get_ydata()), "type": S(["p"]),
            "pch": N([_pch_of(ln)]), "col": S([ln.get_color()]),
        }))
    texts = _texts_by_label(ax, "twopar_text")
    if texts:
        recs.append(("text", {
            "x": N([t.get_position()[0] for t in texts]),
            "y": N([t.get_position()[1] for t in texts]),
            "labels": S([t.get_text() for t in texts]),
        }))
    leg = ax.get_legend()
    if leg is not None:
        handles = leg.legend_handles
        anchor = leg.get_bbox_to_anchor().transformed(ax.transData.inverted())
        recs.append(("legend", {
            "x": N([anchor.x0]), "y": N([anchor.y0]),
            "labels": S([t.get_text() for t in leg.get_texts()]),
            "col": S([h.get_color() for h in handles]),
            "lty": S([_lty_of(h) for h in handles]),
            "lwd": N([h.get_linewidth() for h in handles]),
        }))
    for ln in _line_by_label(ax, "points"):
        recs.append(("points", {
            "x": N(ln.get_xdata()), "y": N(ln.get_ydata()), "type": S(["p"]),
            "pch": N([_pch_of(ln)]), "col": S([ln.get_color()]),
        }))
    lines = out["lines"] or {}
    pts = out["points"] or {}
    recs.append(("out", {
        "distributions": S(lines.get("distributions", [])),
        "col_lines": S(lines.get("col.lines", [])),
        "lty": S(lines.get("lty", [])),
        "lwd": N(lines.get("lwd", [])),
        "twopar": S(out["twopar"] or []),
        "pch": N([pts["pch"]] if pts else []),
        "col_pts": S([pts["col.pts"]] if pts else []),
    }))
    recs.append(("usr", {"v": N(_usr(ax))}))
    return recs


def run_points(fn, args: dict, ax):
    fn(ax=ax, **args)
    return [("points", {
        "x": N(ln.get_xdata()), "y": N(ln.get_ydata()), "type": S([_type_of(ln)]),
        "pch": N([_pch_of(ln)]), "col": S([ln.get_color()]),
    }) for ln in _line_by_label(ax, "points")]


def run_evplot(fn, args: dict, ax):
    plan = fn(ax=ax, **args)
    recs = [("plot", {
        "x": N(plan["x"]), "y": N(plan["y"]), "type": S([plan["type"]]),
    })]
    for ln in _line_by_label(ax, "curve"):
        recs.append(("lines", {"x": N(ln.get_xdata()), "y": N(ln.get_ydata())}))
    rp = plan["rp_axis"]
    if rp is not None:
        ticks = _line_by_label(ax, "rp_tick")
        labels = _texts_by_label(ax, "rp_label")
        recs.append(("axis", {
            "side": N([3]),
            "at": N([ln.get_xdata()[0] for ln in ticks]),
            "labels": S([t.get_text() for t in labels]),
            "pos": N([rp["ypos"]]),
        }))
        title = _texts_by_label(ax, "rp_title")
        recs.append(("text", {
            "x": N([t.get_position()[0] for t in title]),
            "y": N([t.get_position()[1] for t in title]),
            "labels": S([t.get_text() for t in title]),
        }))
    recs.append(("usr", {"v": N(_usr(ax))}))
    return recs


def python_case(group: str, fname: str, args: dict):
    """Run one case in Python on a fresh axes. Returns the records, or an error record."""
    from lmom.evplot import evplot
    from lmom.evplot_default import evplot_default
    from lmom.evpoints import evpoints
    from lmom.lmrdlines import lmrdlines
    from lmom.lmrdpoints import lmrdpoints

    fig, ax = plt.subplots()
    try:
        if group == "lmrd":
            recs = run_lmrd(args, ax)
        elif group == "lmrdpoints":
            recs = run_points(lmrdpoints, args, ax)
        elif group == "lmrdlines":
            recs = run_points(lmrdlines, args, ax)
        elif group == "evpoints":
            recs = run_points(evpoints, args, ax)
        else:
            fn = evplot if fname == "evplot" else evplot_default
            recs = run_evplot(fn, args, ax)
    except (ValueError, NotImplementedError, TypeError) as exc:
        recs = [("error", {"message": S([str(exc)])})]
    finally:
        plt.close(fig)
    return recs


# ---------------------------------------------------------------- comparison
def _norm(field: str, values: list[str]) -> list[str]:
    if field in COLOUR_FIELDS:
        return [to_hex(v) for v in values]
    return values


def compare(r_cases, p_cases, ignored: set) -> dict:
    report = {"cases": len(r_cases), "records": 0, "fields": 0,
              "max_abs_diff": 0.0, "mismatches": [], "ignored_fields": 0}
    if [c for c, _ in r_cases] != [c for c, _ in p_cases]:
        report["mismatches"].append("case lists differ")
        return report
    for (name, r_recs), (_, p_recs) in zip(r_cases, p_cases):
        if len(r_recs) != len(p_recs):
            report["mismatches"].append(f"{name}: {len(r_recs)} R records, {len(p_recs)} Python")
            continue
        for k, ((rf, rfields), (pf, pfields)) in enumerate(zip(r_recs, p_recs)):
            report["records"] += 1
            where = f"{name}[{k}] {rf}"
            if rf != pf:
                report["mismatches"].append(f"{where}: Python record is {pf}")
                continue
            rset = {f for f in rfields if (rf, f) not in ignored}
            pset = {f for f in pfields if (rf, f) not in ignored}
            report["ignored_fields"] += len(set(rfields) | set(pfields)) - len(rset | pset)
            if rset != pset:
                report["mismatches"].append(f"{where}: fields R {sorted(rset)} vs Python {sorted(pset)}")
                continue
            for field in sorted(rset):
                report["fields"] += 1
                rkind, rval = rfields[field]
                pkind, pval = pfields[field]
                if rkind != pkind:
                    report["mismatches"].append(f"{where}.{field}: kind {rkind} vs {pkind}")
                    continue
                if rkind == "s":
                    if _norm(field, rval) != _norm(field, pval):
                        report["mismatches"].append(f"{where}.{field}: {rval} vs {pval}")
                    continue
                if len(rval) != len(pval):
                    report["mismatches"].append(f"{where}.{field}: length {len(rval)} vs {len(pval)}")
                    continue
                a = np.asarray(rval, dtype=float)
                b = np.asarray(pval, dtype=float)
                both_nan = np.isnan(a) & np.isnan(b)
                diff = np.where(both_nan, 0.0, np.abs(a - b))
                diff = np.where(np.isnan(a) ^ np.isnan(b), np.inf, diff)
                worst = float(diff.max()) if diff.size else 0.0
                report["max_abs_diff"] = max(report["max_abs_diff"], worst)
                if worst > TOL:
                    report["mismatches"].append(f"{where}.{field}: max abs diff {worst:.3g}")
    return report


# ---------------------------------------------------------------- timing
def median_seconds(fn) -> float:
    fn()
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return statistics.median(times)


def python_data_call(group: str, fname: str, args: dict):
    """The data step only: no drawing. Returns a zero-argument callable."""
    from lmom.evplot_default import evplot_plan
    from lmom.evpoints import evpoints_data
    from lmom.lmrd import lmrd_plan
    from lmom.lmrdpoints import lmrdpoints_data

    if group == "lmrd":
        fig, ax = plt.subplots()
        pin = float(ax.bbox.width / ax.bbox.height)
        plt.close(fig)
        return lambda: lmrd_plan(pin=pin, **args)
    if group in ("lmrdpoints", "lmrdlines"):
        return lambda: lmrdpoints_data(**args)
    if group == "evpoints":
        return lambda: evpoints_data(**args)
    plan_args = {("type_" if k == "type" else k): v for k, v in args.items()}
    return lambda: evplot_plan(**plan_args)


# ---------------------------------------------------------------- figure
def save_example(group: str, fname: str, args: dict, path: Path) -> None:
    from lmom.evplot_default import evplot_default
    from lmom.evpoints import evpoints
    from lmom.lmrd import lmrd
    from lmom.lmrdlines import lmrdlines
    from lmom.lmrdpoints import lmrdpoints

    fig, ax = plt.subplots(figsize=(6, 5))
    if group == "lmrd":
        lmrd(ax=ax, **args)
    elif group == "lmrdpoints":
        lmrd(ax=ax, distributions="GLO GEV GPA GNO PE3")
        lmrdpoints(ax=ax, **args)
    elif group == "lmrdlines":
        lmrd(ax=ax, distributions="GLO GEV GPA GNO PE3")
        lmrdlines(ax=ax, **args)
    elif group == "evpoints":
        evplot_default(ax=ax, rp_axis=True, y=np.array([3.1, 1.2, 5.5, 2.2, 4.0, 0.7]))
        evpoints(ax=ax, **args)
    else:
        fn = evplot_default
        fn(ax=ax, **args)
    fig.tight_layout()
    fig.savefig(path, format=path.suffix.lstrip("."))
    plt.close(fig)


# ---------------------------------------------------------------- main
def run(fname: str) -> int:
    group = group_of(fname)
    key = fname.replace(".", "_")
    OUT.mkdir(parents=True, exist_ok=True)
    r_values = OUT / f"{key}_r_values.txt"
    r_time = OUT / f"{key}_r_time.txt"
    subprocess.run(["Rscript", str(HERE / "draw_r_proof.R"), fname, key,
                    str(r_values), str(r_time)], cwd=ROOT, check=True)

    cases = load_cases(group)
    r_cases = read_records(r_values)
    p_cases = []
    for case in cases:
        args = to_python_args(case["args"])
        p_cases.append((case["name"], python_case(group, fname, args)))
    py_values = OUT / f"{key}_python_values.txt"
    write_records(py_values, p_cases)

    report = compare(r_cases, p_cases, IGNORED.get(group, set()))

    primary = next(c for c in cases if c.get("primary"))
    args = to_python_args(primary["args"])
    py_fn = python_data_call(group, fname, args)
    py_s = median_seconds(py_fn)
    r_s = float(r_time.read_text())
    save_example(group, fname, args, OUT / f"{key}_example.svg")

    matches = not report["mismatches"] and report["max_abs_diff"] <= TOL
    lines = [
        f"function: {fname}",
        f"matches: {'yes' if matches else 'no'}",
        f"cases: {report['cases']}",
        f"records_compared: {report['records']}",
        f"fields_compared: {report['fields']}",
        f"max_abs_diff: {report['max_abs_diff']:.3e}",
        f"tolerance: {TOL:g}",
        f"timed_case: {primary['name']}",
        f"r_ms: {r_s * 1000:.6g}",
        f"translated_ms: {py_s * 1000:.6g}",
        f"speedup: {r_s / py_s:.4g}",
        f"ignored_device_fields: {sorted(IGNORED.get(group, set()))}",
    ]
    if report["mismatches"]:
        lines.append("mismatches:")
        lines.extend(f"  {m}" for m in report["mismatches"])
    (OUT / f"{key}_proof.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if matches else 1
