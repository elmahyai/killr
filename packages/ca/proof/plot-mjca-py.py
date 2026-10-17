"""Proof for plot.mjca (ca 0.72), Python side.

The inputs are the R mjca object that plot-mjca-r.R wrote, so both sides plot the
same numbers. The translated plot_mjca_data is compared with what R recorded:
principal coordinates, point and label coordinates, symbols (pch), colours,
cex, axis limits and axis titles. Each case is also drawn on a 7 x 7 inch
figure with R's default plot region, and the drawn artists are checked against
the computed data. Timing covers the data computation only (1 untimed + 20 timed).
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
from ca.plot_ca import draw_axes_frame, draw_plot_ops  # noqa: E402
from ca.plot_mjca import plot_mjca_data  # noqa: E402

OUT = Path("packages/ca/docs/output")
TOL = 1e-8
NAME = "plot-mjca"


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
    """The mjca fields plot.mjca reads, rebuilt from the R object."""
    sv = np.array(R[f"{prefix}.sv"], dtype=float)
    k = len(sv)
    rowcoord = np.array(R[f"{prefix}.rowcoord"], dtype=float).reshape(-1, k)
    colcoord = np.array(R[f"{prefix}.colcoord"], dtype=float).reshape(-1, k)
    factors = RAW[f"{prefix}.factors"]
    level_names = RAW[f"{prefix}.levels"]
    factor_names = list(dict.fromkeys(factors))
    levels = [[lev for f, lev in zip(factors, level_names) if f == name]
              for name in factor_names]
    return {
        "sv": sv,
        "rowcoord": rowcoord,
        "colcoord": colcoord,
        "rowmass": np.array(R[f"{prefix}.rowmass"], dtype=float),
        "colmass": np.array(R[f"{prefix}.colmass"], dtype=float),
        "rownames": RAW[f"{prefix}.rownames"],
        "factor_names": factor_names,
        "levels": levels,
        "lambda": RAW[f"{prefix}.lambda"][0],
        "colsup": [int(v) - 1 for v in R[f"{prefix}.colsup"]],
    }


M1 = make_obj("M1")

CASES = {
    "A": dict(),
    "B": dict(what=("all", "all"), map="symbiplot", mass=(True, True), collabels="level"),
    "C": dict(what=("all", "all"), map="colprincipal", contrib=("absolute", "absolute"),
              labels=(1, 2), collabels="factor"),
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
    put(f"{label}.result.rows", res["rows"].ravel().tolist())
    put(f"{label}.result.rownames", res["rows_names"])
    put(f"{label}.result.cols", res["cols"].ravel().tolist())
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


def compare():
    report = []
    failures = []
    max_diff = 0.0
    py = {}
    for label, kwargs in CASES.items():
        data = plot_mjca_data(M1, pin=PDF_PIN, **kwargs)
        py.update(emit_case(label, data))
    r_keys = [k for k in R if k.split(".")[0] in CASES]
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
    extra = [k for k in py if k not in R]
    return len(r_keys), failures, max_diff, extra


def draw_check(label, kwargs):
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_axes([0.82 / 7, 1.02 / 7, 5.76 / 7, 5.16 / 7])
    data = plot_mjca_data(M1, pin=axes_pin(ax), **kwargs)
    draw_axes_frame(ax, data)
    draw_plot_ops(ax, data)
    problems = []
    if not np.allclose(ax.get_xlim(), data["xlim"], atol=TOL, rtol=0):
        problems.append("xlim not set")
    if not np.allclose(ax.get_ylim(), data["ylim"], atol=TOL, rtol=0):
        problems.append("ylim not set")
    drawn_pts, expected_pts = [], []
    for op in data["ops"]:
        if op["kind"] == "points":
            col = op["col"]
            for i in range(len(op["x"])):
                if col[i % len(col)] is None:
                    continue
                expected_pts.append((op["x"][i], op["y"][i]))
    for coll in ax.collections:
        off = np.asarray(coll.get_offsets())
        if off.size:
            drawn_pts.extend(map(tuple, off.tolist()))
    if len(drawn_pts) != len(expected_pts):
        problems.append(f"points drawn {len(drawn_pts)} vs {len(expected_pts)}")
    elif expected_pts:
        a = np.array(sorted(drawn_pts))
        b = np.array(sorted(expected_pts))
        if np.max(np.abs(a - b)) > TOL:
            problems.append("drawn point coordinates differ")
    drawn_txt = sorted((t.get_position()[0], t.get_position()[1], t.get_text())
                       for t in ax.texts)
    exp_txt = []
    for op in data["ops"]:
        if op["kind"] == "text":
            for x, y, lab in zip(op["x"], op["y"], op["labels"]):
                if lab is None or not np.isfinite(x) or not np.isfinite(y):
                    continue
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
    if len(ax.lines) - 2 != n_lines:
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
    n_keys, failures, max_diff, extra = compare()
    draw_failures = {}
    for label, kwargs in CASES.items():
        problems = draw_check(label, kwargs)
        if problems:
            draw_failures[label] = problems

    r_ms = float(read_r(OUT / f"{NAME}-r-ms.txt")["median_ms"][0])
    py_ms = bench(lambda: plot_mjca_data(M1, pin=PDF_PIN))
    (OUT / f"{NAME}-py-ms.txt").write_text(
        f"function\tplot.mjca\nmedian_ms\t{py_ms:.17g}\n"
        "timing\tplot_mjca_data only (no drawing), 1 untimed + 20 timed\n")
    speedup = r_ms / py_ms
    matches = not failures and not draw_failures and not extra
    lines = [
        "function\tplot.mjca",
        f"matches\t{'yes' if matches else 'no'}",
        f"tolerance\t{TOL}",
        f"compared_keys\t{n_keys}",
        "compared_quantities\tprincipal (xy) coordinates, point coordinates, label coordinates,"
        " pch symbols, colours, cex, axis limits, axis titles",
        f"max_abs_diff\t{max_diff:.3g}",
        f"r_ms\t{r_ms:.6g}",
        f"translated_ms\t{py_ms:.6g}",
        f"speedup\t{speedup:.4g}",
        "cases\tA default (what none/all); B symbiplot with mass and collabels level; "
        "C colprincipal with absolute contributions, labels c(1,2), collabels factor",
        "figures\tplot-mjca-A.svg, plot-mjca-B.svg, plot-mjca-C.svg",
        "not_compared\tadjusted or JCA lambda (axis percentages need inertia.e, "
        "which the translated mjca result does not return)",
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
