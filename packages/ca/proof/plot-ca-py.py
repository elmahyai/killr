"""Proof for plot.ca (ca 0.72), Python side.

The inputs are the R ca objects that plot-ca-r.R wrote, so both sides plot the
same numbers. The translated plot_ca_data is compared with what R recorded:
principal coordinates, point and label coordinates, symbols (pch), colours,
axis limits and axis titles. Each case is also drawn on a 7 x 7 inch figure
with R's default plot region, and the drawn artists are checked against the
computed data. Timing covers the data computation only (1 untimed + 20 timed).
"""

import sys
import time
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "packages/ca")
from ca._plotcommon import axes_pin  # noqa: E402
from ca._rgraphics import PDF_PIN  # noqa: E402
from ca.plot_ca import draw_axes_frame, draw_plot_ops, plot_ca_data  # noqa: E402

OUT = Path("packages/ca/docs/output")
TOL = 1e-8
NAME = "plot-ca"


def read_r(path):
    raw = {}
    for line in path.read_text().splitlines():
        parts = line.split("\t")
        raw[parts[0]] = parts[1:]
    return raw


def num(v):
    if v == "NA":
        return float("nan")
    try:
        return float(v)
    except ValueError:
        return v


RAW = read_r(OUT / f"{NAME}-r-values.txt")
R = {k: [num(x) for x in vals] for k, vals in RAW.items()}


def make_obj(prefix):
    sv = np.array(R[f"{prefix}.sv"], dtype=float)
    k = len(sv)
    rowcoord = np.array(R[f"{prefix}.rowcoord"], dtype=float).reshape(-1, k)
    colcoord = np.array(R[f"{prefix}.colcoord"], dtype=float).reshape(-1, k)
    return {
        "sv": sv,
        "rowcoord": rowcoord,
        "colcoord": colcoord,
        "rowmass": np.array(R[f"{prefix}.rowmass"], dtype=float),
        "colmass": np.array(R[f"{prefix}.colmass"], dtype=float),
        "rowinertia": np.array(R[f"{prefix}.rowinertia"], dtype=float),
        "colinertia": np.array(R[f"{prefix}.colinertia"], dtype=float),
        "rownames": RAW[f"{prefix}.rownames"],
        "colnames": RAW[f"{prefix}.colnames"],
        "rowsup": [int(v) - 1 for v in R[f"{prefix}.rowsup"]],
        "colsup": [int(v) - 1 for v in R[f"{prefix}.colsup"]],
    }


O1 = make_obj("O1")
O2 = make_obj("O2")

CASES = {
    "A": (O1, dict()),
    "B": (O2, dict(map="symbiplot")),
    "C": (O1, dict(map="rowgab", mass=(True, True), contrib=("relative", "absolute"),
                   lines=(True, False), labels=(2, 1))),
}


def fmt(v):
    if v is None:
        return float("nan")
    if isinstance(v, (float, int, np.floating, np.integer)):
        return float(v)
    return str(v)


def emit_case(label, data):
    P = {}

    def put(key, values):
        P[key] = [fmt(v) for v in values]

    put(f"{label}.xlim", data["xlim"])
    put(f"{label}.ylim", data["ylim"])
    put(f"{label}.xlab", [data["xlab"]])
    put(f"{label}.ylab", [data["ylab"]])
    res = data["result"]
    for side in ("rows", "cols"):
        coords = res[side]
        put(f"{label}.result.{side}", [] if coords is None else coords.ravel().tolist())
    put(f"{label}.result.rownames", res["rows_names"] or [])
    put(f"{label}.result.colnames", res["colnames"])
    for k, op in enumerate(data["ops"], start=1):
        p = f"{label}.{k}"
        put(f"{p}.kind", [op["kind"]])
        put(f"{p}.x", op["x"])
        put(f"{p}.y", op["y"])
        if "pch" in op:
            put(f"{p}.pch", op["pch"])
            put(f"{p}.cex", op["cex"])
        if "labels" in op:
            put(f"{p}.labels", op["labels"])
        put(f"{p}.col", op["col"])
    return P


def same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        if np.isnan(a) and np.isnan(b):
            return True, 0.0
        if np.isnan(a) or np.isnan(b):
            return False, float("inf")
        d = abs(a - b)
        return d <= TOL, d
    return a == b, 0.0


TEXT_KEYS = (".labels", "rownames", "colnames", ".kind", ".col", ".xlab", ".ylab")


def compare(prefixes):
    report = []
    max_diff = 0.0
    failures = []
    py = {}
    for label, (obj, kwargs) in CASES.items():
        if label not in prefixes:
            continue
        data = plot_ca_data(obj, pin=PDF_PIN, **kwargs)
        py.update(emit_case(label, data))
    r_keys = [k for k in R if k.split(".")[0] in prefixes]
    for key in r_keys:
        if key not in py:
            failures.append(f"missing {key}")
            continue
        rv, pv = R[key], py[key]
        if key.endswith(TEXT_KEYS):
            # labels, names, kinds and colours are text: compare the raw R text
            rv = RAW[key]
            pv = ["NA" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in pv]
            if rv == pv:
                report.append(key)
                continue
            failures.append(f"{key}: R {rv!r} vs Python {pv!r}")
            continue
        if len(rv) != len(pv):
            failures.append(f"{key}: length {len(rv)} vs {len(pv)}")
            continue
        for a, b in zip(rv, pv):
            ok, d = same(a, b)
            if isinstance(a, float) and isinstance(b, float) and not np.isnan(a):
                max_diff = max(max_diff, d)
            if not ok:
                failures.append(f"{key}: R {a!r} vs Python {b!r}")
                break
        report.append(key)
    extra = [k for k in py if k not in R]
    return report, failures, max_diff, extra


def draw_check(label, obj, kwargs):
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_axes([0.82 / 7, 1.02 / 7, 5.76 / 7, 5.16 / 7])
    data = plot_ca_data(obj, pin=axes_pin(ax), **kwargs)
    draw_axes_frame(ax, data)
    draw_plot_ops(ax, data)
    problems = []
    if not np.allclose(ax.get_xlim(), data["xlim"], atol=TOL, rtol=0):
        problems.append("xlim not set")
    if not np.allclose(ax.get_ylim(), data["ylim"], atol=TOL, rtol=0):
        problems.append("ylim not set")
    drawn_pts = []
    expected_pts = []
    for op in data["ops"]:
        if op["kind"] == "points":
            col = op["col"]
            for i in range(len(op["x"])):
                c = col[i % len(col)]
                if c is None:
                    continue
                expected_pts.append((op["x"][i], op["y"][i]))
    for coll in ax.collections:
        off = np.asarray(coll.get_offsets())
        if off.size:
            drawn_pts.extend(map(tuple, off.tolist()))
    if len(drawn_pts) != len(expected_pts):
        problems.append(f"points drawn {len(drawn_pts)} vs {len(expected_pts)}")
    else:
        a = np.array(sorted(drawn_pts))
        b = np.array(sorted(expected_pts))
        if a.size and np.max(np.abs(a - b)) > TOL:
            problems.append("drawn point coordinates differ")
    drawn_txt = sorted((t.get_position()[0], t.get_position()[1], t.get_text())
                       for t in ax.texts)
    exp_txt = []
    for op in data["ops"]:
        if op["kind"] == "text":
            for x, y, lab in zip(op["x"], op["y"], op["labels"]):
                if lab is None or not np.isfinite(x) or not np.isfinite(y):
                    continue  # R's NA label is not drawn
                exp_txt.append((x, y, str(lab)))
    exp_txt.sort()
    if len(drawn_txt) != len(exp_txt):
        problems.append(f"texts drawn {len(drawn_txt)} vs {len(exp_txt)}")
    else:
        for (ax_, ay, at), (bx, by, bt) in zip(drawn_txt, exp_txt):
            if abs(ax_ - bx) > TOL or abs(ay - by) > TOL or at != bt:
                problems.append("drawn label position or text differs")
                break
    n_lines = sum(1 for op in data["ops"] if op["kind"] == "lines")
    if len(ax.lines) - 2 != n_lines:  # two dotted zero lines are axhline/axvline
        problems.append(f"lines drawn {len(ax.lines) - 2} vs {n_lines}")
    fig.savefig(OUT / f"{NAME}-{label}.svg", format="svg")
    plt.close(fig)
    return problems


def bench(fn, repeats=20):
    fn()
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000.0)
    return float(np.median(times))


def main():
    report, failures, max_diff, extra = compare(set(CASES))
    draws = {label: draw_check(label, obj, kwargs) for label, (obj, kwargs) in CASES.items()}
    draw_failures = {k: v for k, v in draws.items() if v}

    r_ms = float(read_r(OUT / f"{NAME}-r-ms.txt")["median_ms"][0])
    py_ms = bench(lambda: plot_ca_data(O1, pin=PDF_PIN))
    (OUT / f"{NAME}-py-ms.txt").write_text(
        f"function\tplot.ca\nmedian_ms\t{py_ms:.17g}\n"
        "timing\tplot_ca_data only (no drawing), 1 untimed + 20 timed\n")
    speedup = r_ms / py_ms
    matches = not failures and not draw_failures and not extra
    lines = [
        f"function\tplot.ca",
        f"matches\t{'yes' if matches else 'no'}",
        f"tolerance\t{TOL}",
        f"compared_keys\t{len(report)}",
        f"compared_quantities\tprincipal (xy) coordinates, point coordinates, label coordinates,"
        " pch symbols, colours, cex, axis limits, axis titles, line coordinates",
        f"max_abs_diff\t{max_diff:.3g}",
        f"r_ms\t{r_ms:.6g}",
        f"translated_ms\t{py_ms:.6g}",
        f"speedup\t{speedup:.4g}",
        "cases\tA default; B symbiplot with supplementary row and column; "
        "C rowgab with mass, relative and absolute contributions, lines, labels c(2,1)",
        "figures\tplot-ca-A.svg, plot-ca-B.svg, plot-ca-C.svg",
    ]
    if failures:
        lines.append("failures\t" + " | ".join(failures[:20]))
    if draw_failures:
        lines.append("drawing\t" + " | ".join(f"{k}: {v}" for k, v in draw_failures.items()))
    if extra:
        lines.append("extra_keys\t" + ", ".join(extra[:20]))
    (OUT / f"{NAME}-compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
