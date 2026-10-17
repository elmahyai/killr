"""Proof for plot3d.ca (ca 0.72), Python side.

The inputs are the R ca objects that plot3d-ca-r.R wrote, so both sides compute
the same 3D map. The translated plot3d_ca_data is compared with the rgl calls R
recorded: the axis lines and titles, every symbol vertex for each pch (spheres,
triangles, quads and lines, with their radii), the point and label positions,
colours and alpha. Each case is also drawn on a 3D axes and saved as an SVG.
Timing covers the data computation only (1 untimed + 20 timed).
"""

import sys
import time
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "packages/ca")
from ca._rgraphics import PDF_PIN  # noqa: E402
from ca._plot3d_draw import draw_plot3d_ops  # noqa: E402
from ca.plot3d_ca import plot3d_ca_data  # noqa: E402

OUT = Path("packages/ca/docs/output")
TOL = 1e-8
NAME = "plot3d-ca"
TEXT_KEYS = (".labels", "rownames", "colnames", ".kind", ".col", ".fn", ".text")


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


O3 = make_obj("O3")
O4 = make_obj("O4")
CASES = {
    "A": (O3, dict()),
    "B": (O4, dict(map="symbiplot")),
    "C": (O3, dict(map="rowprincipal", contrib=("relative", "absolute"),
                   labels=(1, 2), sf=0.001)),
}


def fmt(v):
    if v is None:
        return float("nan")
    if isinstance(v, (float, int, np.floating, np.integer)):
        return float(v)
    return str(v)


def records_to_keys(label, ops):
    """Flatten the primitive records into the same keys the R proof writes."""
    P = {}

    def put(key, values):
        if isinstance(values, str):
            P[key] = [values]
            return
        P[key] = [fmt(v) for v in np.atleast_1d(values)]

    for k, op in enumerate(ops, start=1):
        p = f"{label}.{k}"
        put(f"{p}.fn", op["fn"])
        if op["fn"] == "plot3d":
            continue
        put(f"{p}.x", op["x"])
        put(f"{p}.y", op["y"])
        put(f"{p}.z", op["z"])
        if op["fn"] == "texts3d":
            put(f"{p}.text", op["text"])
            put(f"{p}.cex", [op["cex"]])
        elif op["fn"] == "spheres3d" and op.get("radius") is not None:
            put(f"{p}.radius", [op["radius"]])
        if op.get("col") is not None:
            put(f"{p}.col", [op["col"]])
        if op.get("alpha") is not None:
            put(f"{p}.alpha", np.atleast_1d(op["alpha"]))
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


def compare():
    report = []
    failures = []
    max_diff = 0.0
    py = {}
    for label, (obj, kwargs) in CASES.items():
        data = plot3d_ca_data(obj, pin=PDF_PIN, **kwargs)
        py.update(records_to_keys(label, data["ops"]))
    r_keys = [k for k in R if k.split(".")[0] in CASES]
    for key in r_keys:
        if key not in py:
            failures.append(f"missing {key}")
            continue
        rv, pv = R[key], py[key]
        if key.endswith(TEXT_KEYS):
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
        ok_all = True
        for a, b in zip(rv, pv):
            ok, d = same(a, b)
            if isinstance(a, float) and isinstance(b, float) and not np.isnan(a):
                max_diff = max(max_diff, d)
            if not ok:
                failures.append(f"{key}: R {a!r} vs Python {b!r}")
                ok_all = False
                break
        if ok_all:
            report.append(key)
    extra = [k for k in py if k not in R]
    return report, failures, max_diff, extra


def draw_check(label, obj, kwargs):
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(projection="3d")
    data = plot3d_ca_data(obj, pin=PDF_PIN, **kwargs)
    ax.set_xlim(*data["xlim"])
    ax.set_ylim(*data["ylim"])
    ax.set_zlim(*data["zlim"])
    draw_plot3d_ops(ax, data["ops"])
    fig.savefig(OUT / f"{NAME}-{label}.svg", format="svg")
    plt.close(fig)
    n_prim = sum(1 for op in data["ops"] if op["fn"] != "plot3d")
    return n_prim


def bench(fn, repeats=20):
    fn()
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000.0)
    return float(np.median(times))


def main():
    report, failures, max_diff, extra = compare()
    drawn = {label: draw_check(label, obj, kwargs) for label, (obj, kwargs) in CASES.items()}

    r_ms = float(read_r(OUT / f"{NAME}-r-ms.txt")["median_ms"][0])
    py_ms = bench(lambda: plot3d_ca_data(O3, pin=PDF_PIN))
    (OUT / f"{NAME}-py-ms.txt").write_text(
        f"function\tplot3d.ca\nmedian_ms\t{py_ms:.17g}\n"
        "timing\tplot3d_ca_data only (no drawing), 1 untimed + 20 timed\n")
    speedup = r_ms / py_ms
    matches = not failures and not extra
    lines = [
        "function\tplot3d.ca",
        f"matches\t{'yes' if matches else 'no'}",
        f"tolerance\t{TOL}",
        f"compared_keys\t{len(report)}",
        "compared_quantities\taxis lines and titles, every symbol vertex for each pch "
        "(spheres, triangles, lines, radii), point and label coordinates, colours, alpha, cex",
        f"max_abs_diff\t{max_diff:.3g}",
        f"r_ms\t{r_ms:.6g}",
        f"translated_ms\t{py_ms:.6g}",
        f"speedup\t{speedup:.4g}",
        "cases\tA ca(5 x 4 table), default; B symbiplot with supplementary row and column "
        "(pch 1 and 9); C rowprincipal with relative and absolute contributions, sf 0.001",
        "primitives_drawn\t" + ", ".join(f"{k}={v}" for k, v in drawn.items()),
        "figures\tplot3d-ca-A.svg, plot3d-ca-B.svg, plot3d-ca-C.svg",
        "rgl\tthe rgl package needs an OpenGL display, so R's rgl calls are recorded by a "
        "stand-in package (draws nothing); Python draws with Matplotlib 3D axes",
    ]
    if failures:
        lines.append("failures\t" + " | ".join(failures[:20]))
    if extra:
        lines.append("extra_keys\t" + ", ".join(extra[:20]))
    (OUT / f"{NAME}-compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
