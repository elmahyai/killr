"""Proof for multilines (ca 0.72), Python side.

The same inputs as multilines-r.R are passed to the translated ``multilines_data``.
Each returned record (x, y, type, col, lwd) is compared with the lines() call
that R recorded for the same group, within 1e-8 for numbers and exactly for
text. ``NA`` in R corresponds to ``None`` here. Timing covers the data
computation only, on the 2000-point dataset: 1 untimed call, then the median
of 20 timed calls. Drawing is checked separately by ``multilines`` returning
the same records and by a saved SVG.
"""

import sys
import time
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "packages/ca")
from ca.multilines import multilines, multilines_data  # noqa: E402

OUT = Path("packages/ca/docs/output")
TOL = 1e-8
NAME = "multilines"


def read_r(path):
    raw = {}
    for line in path.read_text().splitlines():
        parts = line.split("\t")
        raw[parts[0]] = parts[1:]
    return raw


RAW = read_r(OUT / f"{NAME}-r-values.txt")


def r_numbers(vals):
    if vals == ["NA"]:
        return [float("nan")]
    return [float(v) for v in vals]


# Case inputs, as in multilines-r.R
XY_A = np.column_stack([
    [5, 1, 3, 2, 4, 9, 7, 8, 6, 10, 2, 1],
    [50, 10, 30, 20, 40, 90, 70, 80, 60, 100, 25, 12],
]).astype(float)
GRP_A = ["zeta", "alpha", "mid"] * 4
n_B = 60
i_B = np.arange(1, n_B + 1)
XY_B = np.column_stack([
    np.round(np.linspace(0, 10, n_B) + np.sin(i_B), 6),
    np.round((i_B * 37) % 53 + 0.5, 6),
])
GRP_B = [int(v) for v in np.tile(np.arange(1, 11), 6)]
XY_C = np.array([[3, 9], [1, 7], [2, 8], [5, 1], [4, 2]], dtype=float)

n_T = 2000
i_T = np.arange(1, n_T + 1)
XY_T = np.column_stack([
    (i_T * 7919) % 1000 / 10.0,
    (i_T * 104729) % 997 / 7.0,
])
GRP_T = [int(v) for v in (i_T % 5) + 1]


def translated_records():
    recs = {}
    recs["A"] = multilines_data(XY_A, group=GRP_A)
    recs["B"] = multilines_data(XY_B, group=GRP_B, which=[2, 5, 10], sort=2,
                                type="o", col=["red", "blue"], lwd=[1, 2])
    recs["C"] = multilines_data(XY_C, type="p", sort=0)
    return recs


def compare():
    recs = translated_records()
    report = []
    failures = []
    max_diff = 0.0
    for case, group_recs in recs.items():
        for k, rec in enumerate(group_recs, start=1):
            p = f"{case}.{k}"
            for field in ("x", "y", "type", "col", "lwd"):
                key = f"{p}.{field}"
                if key not in RAW:
                    failures.append(f"missing R key {key}")
                    continue
                rv = RAW[key]
                pv = rec[field]
                if field in ("type", "col"):
                    r_text = rv[0] if rv else ""
                    p_text = "NA" if pv is None else str(pv)
                    if r_text == p_text:
                        report.append(key)
                    else:
                        failures.append(f"{key}: R {r_text!r} vs Python {p_text!r}")
                    continue
                if field == "lwd":
                    r_val = float("nan") if rv == ["NA"] else float(rv[0])
                    p_val = float("nan") if pv is None else float(pv)
                    rlist = [r_val]
                    plist = [p_val]
                else:
                    rlist = r_numbers(rv)
                    plist = np.asarray(pv, dtype=float).tolist()
                if len(rlist) != len(plist):
                    failures.append(f"{key}: length {len(rlist)} vs {len(plist)}")
                    continue
                ok = True
                for a, b in zip(rlist, plist):
                    if np.isnan(a) or np.isnan(b):
                        if not (np.isnan(a) and np.isnan(b)):
                            ok = False
                        continue
                    d = abs(a - b)
                    max_diff = max(max_diff, d)
                    if d > TOL:
                        ok = False
                if ok:
                    report.append(key)
                else:
                    failures.append(f"{key}: R {rlist} vs Python {plist}")
    r_keys = [k for k in RAW if k.split(".")[0] in recs]
    return report, failures, max_diff, len(r_keys)


def bench(fn, repeats=20):
    fn()
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000.0)
    return float(np.median(times))


def draw_check():
    fig, ax = plt.subplots(figsize=(7, 7))
    recs = multilines(XY_A, group=GRP_A, ax=ax)
    fig.savefig(OUT / f"{NAME}.svg", format="svg")
    plt.close(fig)
    return len(recs), sum(1 for r in recs if r["col"] is not None)


def main():
    report, failures, max_diff, n_r = compare()
    n_lines, n_drawn = draw_check()

    r_ms = float(read_r(OUT / f"{NAME}-r-ms.txt")["median_ms"][0])
    py_ms = bench(lambda: multilines_data(XY_T, group=GRP_T))
    (OUT / f"{NAME}-py-ms.txt").write_text(
        "function\tmultilines\n"
        f"median_ms\t{py_ms:.17g}\n"
        "timing\tmultilines_data call on 2000 points, 5 groups; 1 untimed + 20 timed\n")
    speedup = r_ms / py_ms
    matches = not failures and len(report) == n_r
    lines = [
        "function\tmultilines",
        f"matches\t{'yes' if matches else 'no'}",
        f"tolerance\t{TOL}",
        f"compared_keys\t{len(report)} of {n_r}",
        "compared_quantities\tper lines() call: x, y, type, col, lwd, for cases A "
        "(default palette, 3 groups, sort 1), B (10 groups, which, sort 2, type o, "
        "col and lwd indexed past their length give NA), C (no group, type p, sort 0)",
        f"max_abs_diff\t{max_diff:.3g}",
        f"r_ms\t{r_ms:.6g}",
        f"translated_ms\t{py_ms:.6g}",
        f"speedup\t{speedup:.4g}",
        f"drawn\t{n_drawn} of {n_lines} records drawn in case A (figure multilines.svg)",
    ]
    if failures:
        lines.append("failures\t" + " | ".join(failures[:20]))
    (OUT / f"{NAME}-compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
