"""Proof for crates/logspline: the Rust kernel against the R .C entry points.

Run from the repository root after kernel-r.R:

    .venv/bin/python packages/logspline/proof/kernel-py.py

It runs the same fixed inputs as kernel-r.R through the Rust kernel, writes
docs/output/kernel-py.csv, and compares every output with
docs/output/kernel-r.csv (max absolute difference, tolerance 1e-8). Timing:
one untimed pass, then the median of 20 timed passes with time.perf_counter().
The result is written to docs/output/kernel-compare.txt.
"""

import math
import os
import statistics
import time

import numpy as np

import logspline as ls

OUT = "packages/logspline/docs/output"
TOL = 1e-8

# Fixed sample, the same arithmetic as kernel-r.R.
n = 200
idx = range(1, n + 1)
x = [((i * i * 37) % 997) / 100.0 + i / 50.0 for i in idx]
xs = sorted(x)
nu = len(set(x))

q = [j * 0.14 for j in range(100)]
p = [j / 100 for j in range(1, 100)]

LC_NAMES = ["delete", "iautoknot", "sample", "nsample", "bd", "SorC", "nk",
            "kt", "cf", "penalty", "wk", "wk2", "logl"]


def I(a):
    return np.array(a, dtype=np.int32)


def F(a):
    return np.array(a, dtype=np.float64)


def nlfit(maxp, ilow, low, iupp, upp):
    return ls.nlogcensor(
        I([n, 0, 0, 0, 1 - ilow, 1 - iupp, -1]),
        F(xs + [0.0] * maxp),
        F([-1.0, low, upp]),
        F([0.0] * maxp),
        I([0] * maxp),
        F([0.0] * maxp),
    )


def rpq(z, ilow, low, iupp, upp):
    nk = int(z["ip"][1])
    coef = F(z["coef"][: nk + 2])          # c(coef.pol, coef.kts)
    knots = F(z["kts"][:nk])
    bnd = F([ilow, low, iupp, upp])
    dens = ls.rpqlsd(coef, knots, bnd, 1, F(q), len(knots), len(q))
    quant = ls.rpqlsd(coef, knots, bnd, 0, F(p), len(knots), len(p))
    return {"density": {"pq": dens["pq"]}, "quantile": {"pq": quant["pq"]}}


def pipeline():
    n1 = 4 * n ** 0.2 + 1
    nsample = [n, n, 0, 0, 0, nu - 1]
    knots = [0.0] * 50
    sorc = [0] * 35
    sorc[0] = 1
    sorc[16] = 0
    lc = ls.logcensor(
        I([1, 0, 0, 0, 0]),
        I([1, 0, 0, 0, 0]),
        F(x + [0.0] * 4),
        I(nsample + [0] * 4),
        F([1.0, 0.0, 0.0, 0.0, 0.0]),
        I(sorc + [0] * 4),
        0,
        F(knots + [0.0] * 4),
        F(knots + [0.0] * 4),
        F([math.log(n), 0.0, 0.0, 0.0, 0.0]),
        F(x + [0.0] * 4),
        F(x + [0.0] * 4),
        F([0.0] * int(math.floor(n1 + 11))),
    )

    nx = ls.nlogcensorx(I([-100] + [0] * 9))
    maxp = int(nx["z"][0])
    fit_a = nlfit(maxp, 0, 0.0, 0, 0.0)
    r_a = rpq(fit_a, 0, 0.0, 0, 0.0)
    fit_b = nlfit(maxp, 1, -0.5, 1, 15.0)
    r_b = rpq(fit_b, 1, -0.5, 1, 15.0)

    return {
        "logcensor": lc,
        "nlogcensorx": nx,
        "nlogcensor_unbounded": fit_a,
        "rpqlsd_unbounded_density": r_a["density"],
        "rpqlsd_unbounded_quantile": r_a["quantile"],
        "nlogcensor_bounded": fit_b,
        "rpqlsd_bounded_density": r_b["density"],
        "rpqlsd_bounded_quantile": r_b["quantile"],
    }


def flatten(res):
    """Rows (label, name, index, value) in the same order as kernel-r.csv."""
    rows = []
    for label, z in res.items():
        if label == "logcensor":
            names = LC_NAMES
        else:
            names = list(z.keys())
        for name in names:
            v = np.asarray(z[name], dtype=np.float64).ravel()
            for k, val in enumerate(v):
                rows.append((label, name, k, float(val)))
    return rows


def read_r_csv(path):
    rows = {}
    with open(path) as fh:
        next(fh)
        for line in fh:
            label, name, index, value = line.rstrip("\n").split(",")
            rows[(label, name, int(index))] = float(value)
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)

    # untimed pass: outputs
    res = pipeline()
    rows = flatten(res)
    with open(os.path.join(OUT, "kernel-py.csv"), "w") as fh:
        fh.write("label,name,index,value\n")
        for label, name, k, val in rows:
            fh.write(f"{label},{name},{k},{val:.17g}\n")

    # timed passes
    ms = []
    for _ in range(20):
        t0 = time.perf_counter()
        pipeline()
        ms.append((time.perf_counter() - t0) * 1000.0)
    with open(os.path.join(OUT, "kernel-py-timing.csv"), "w") as fh:
        fh.write("run,ms\n")
        for r, v in enumerate(ms, start=1):
            fh.write(f"{r},{v:.6f}\n")

    # compare with R
    r_rows = read_r_csv(os.path.join(OUT, "kernel-r.csv"))
    py_rows = {(label, name, k): val for label, name, k, val in rows}
    if set(r_rows) != set(py_rows):
        missing = set(r_rows) ^ set(py_rows)
        raise SystemExit(f"output shapes differ, {len(missing)} keys do not match")

    worst = (0.0, None)
    for key, rv in r_rows.items():
        d = abs(rv - py_rows[key])
        if d > worst[0]:
            worst = (d, key)
    max_abs_diff = worst[0]

    r_times = []
    with open(os.path.join(OUT, "kernel-r-timing.csv")) as fh:
        next(fh)
        for line in fh:
            r_times.append(float(line.split(",")[1]))
    r_ms = statistics.median(r_times)
    t_ms = statistics.median(ms)

    status = "PASS" if max_abs_diff <= TOL else "FAIL"
    lines = [
        "logspline 2.1.22 kernel proof: crates/logspline (Rust) vs R .C entry points",
        f"status: {status} (tolerance {TOL:g})",
        f"outputs compared: {len(r_rows)}",
        f"max_abs_diff: {max_abs_diff:.6g}",
        f"worst at: {worst[1]}",
        f"r_ms (median of 20, Sys.time): {r_ms:.4f}",
        f"translated_ms (median of 20, perf_counter): {t_ms:.4f}",
        f"speedup (r_ms / translated_ms): {r_ms / t_ms:.3f}",
        "pipeline: logcensor, nlogcensorx, nlogcensor (unbounded and bounded), rpqlsd density and quantile for each fit",
    ]
    text = "\n".join(lines) + "\n"
    with open(os.path.join(OUT, "kernel-compare.txt"), "w") as fh:
        fh.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
