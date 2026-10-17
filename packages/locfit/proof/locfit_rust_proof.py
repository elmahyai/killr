"""Proof (Rust side): the crate crates/locfit against R locfit 1.5-9.12.

Run from the repository root after the R side has written its outputs:
    .venv/bin/maturin develop --release --manifest-path crates/locfit/Cargo.toml
    LOCFIT_RLIB=/tmp/locfit-rlib Rscript packages/locfit/proof/locfit_r_proof.R
    .venv/bin/python packages/locfit/proof/locfit_rust_proof.py

Reads the shared inputs and R reference outputs from packages/locfit/docs/output,
calls locfit.locfit_fit on the same data, compares, and writes:
    locfit_rust_<case>_eva.csv   coef | nlx | t0 | lik | h, same layout as R eva$coef
    locfit_rust_timing.csv       median of 20 timed calls, milliseconds
    locfit_compare.txt           max absolute differences and pass/fail per case
Tolerance is 1e-8 (max absolute difference).
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

import locfit

OUT = Path("packages/locfit/docs/output")
TOL = 1e-8

# name, nn (alpha), deg, kt (crate spelling), ev
CASES = [
    ("d1_sph_deg2_data", 0.7, 2, "spherical", "data"),
    ("d2_prod_deg1_data", 0.5, 1, "product", "data"),
    ("d1_sph_deg2_pres", 0.7, 2, "spherical", "pres"),
]


def read_csv(path):
    return np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)


def read_dp_pairs(path):
    out = {}
    with open(path) as fh:
        next(fh)
        for line in fh:
            key, value = line.strip().split(",")
            out[key] = float(value)
    return out


def rust_matrix(res, nc):
    """Stack coef | nlx | t0 | lik | h to match R's eva$coef columns 1..3nc+4."""
    return np.hstack([
        res["coef"],
        res["nlx"],
        res["t0"],
        res["lik"],
        res["h"].reshape(-1, 1),
    ])


def run_case(name, nn, deg, kt, ev):
    data = read_csv(OUT / f"locfit_{name}_data.csv")
    x, y = data[:, :-1], data[:, -1]
    xev = read_csv(OUT / f"locfit_{name}_xev.csv") if ev == "pres" else None
    if xev is not None:
        xev = np.ascontiguousarray(xev)

    def call():
        return locfit.locfit_fit(
            np.ascontiguousarray(x), np.ascontiguousarray(y),
            xev=xev, nn=nn, deg=deg, kern="tricube", kt=kt,
        )

    res = call()  # untimed
    elapsed = []
    for _ in range(20):
        t0 = time.perf_counter()
        call()
        elapsed.append(time.perf_counter() - t0)
    median_ms = statistics.median(elapsed) * 1000.0

    d = x.shape[1]
    nc = d + 1
    mat = rust_matrix(res, nc)
    np.savetxt(
        OUT / f"locfit_rust_{name}_eva.csv", mat, delimiter=",",
        header=",".join(f"c{i + 1}" for i in range(mat.shape[1])),
        comments="", fmt="%.17g",
    )

    r_eva = read_csv(OUT / f"locfit_r_{name}_eva.csv")
    r_mat = r_eva[:, : 3 * nc + 4]  # drop R's final informational column
    assert mat.shape == r_mat.shape, (mat.shape, r_mat.shape)
    eva_diff = float(np.max(np.abs(mat - r_mat)))

    r_dp = read_dp_pairs(OUT / f"locfit_r_{name}_dp.csv")
    rust_dp = {
        "lk": float(res["lk"]),
        "df1": float(res["df0"]),  # locfit dp "df1" is C DT0
        "df2": float(res["df1"]),  # locfit dp "df2" is C DT1
        "rv": float(res["rv"]),
    }
    dp_diff = max(abs(rust_dp[k] - r_dp[k]) for k in ("lk", "df1", "df2", "rv"))

    return {
        "name": name, "shape": mat.shape, "eva_diff": eva_diff,
        "dp_diff": dp_diff, "median_ms": median_ms,
        "rust_dp": rust_dp, "r_dp": r_dp,
    }


def main():
    if not Path("packages/locfit/proof").is_dir():
        sys.exit("run from the repository root")
    OUT.mkdir(parents=True, exist_ok=True)

    results = [run_case(*c) for c in CASES]

    r_timing = {}
    with open(OUT / "locfit_r_timing.csv") as fh:
        next(fh)
        for line in fh:
            case, ms = line.strip().split(",")
            r_timing[case.strip('"')] = float(ms)

    with open(OUT / "locfit_rust_timing.csv", "w") as fh:
        fh.write("case,median_ms\n")
        for r in results:
            fh.write(f"{r['name']},{r['median_ms']:.17g}\n")

    lines = [f"tolerance (max abs diff): {TOL:g}", ""]
    all_pass = True
    for r in results:
        ok = r["eva_diff"] <= TOL and r["dp_diff"] <= TOL
        all_pass = all_pass and ok
        lines += [
            f"case {r['name']}: shape {r['shape'][0]}x{r['shape'][1]}",
            f"  eva (coef,nlx,t0,lik,h) max abs diff: {r['eva_diff']:.3e}",
            f"  dp (lk,df1,df2,rv) max abs diff:      {r['dp_diff']:.3e}",
            f"  R median ms: {r_timing[r['name']]:.6f}   Rust median ms: {r['median_ms']:.6f}",
            f"  result: {'PASS' if ok else 'FAIL'}",
            "",
        ]
    lines.append(f"overall: {'PASS' if all_pass else 'FAIL'}")
    text = "\n".join(lines) + "\n"
    (OUT / "locfit_compare.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
