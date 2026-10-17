"""Proof, Rust side: call the hexbin crate on the same fixed points as R.

Run after the R reference script, from the repository root:

    .venv/bin/python packages/hexbin/proof/hexbin_rust_compare.py

It reads packages/hexbin/docs/output/hexbin-r-reference.csv (written by
hexbin_r_reference.R), calls the four kernels, compares each output within
1e-8, and times one representative hbin call: one untimed call, then the
median of 20 timed calls with time.perf_counter().
"""

from __future__ import annotations

import math
import statistics
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

import hexbin_kernels as hexbin  # the crate's native module, renamed from hexbin

OUT_DIR = Path("packages/hexbin/docs/output")
REF_PATH = OUT_DIR / "hexbin-r-reference.csv"
R_TIMING_PATH = OUT_DIR / "hexbin-r-timing.txt"
RESULT_PATH = OUT_DIR / "hexbin-rust-compare.txt"
TOL = 1e-8


def load_reference(path: Path) -> dict[tuple[str, str], list[float]]:
    data: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    with path.open() as handle:
        next(handle)  # header
        for line in handle:
            kernel, name, index, value = line.rstrip("\n").split(",")
            data[(kernel, name)].append((int(index), value))
    out: dict[tuple[str, str], np.ndarray] = {}
    for key, pairs in data.items():
        pairs.sort()
        values = [v for _, v in pairs]
        if key[0] == "points" or key[1] in {"x", "y", "xcm", "ycm"}:
            out[key] = np.array([float(v) for v in values], dtype=np.float64)
        else:
            out[key] = np.array([int(v) for v in values], dtype=np.int64)
    return out


def points(n: int) -> tuple[np.ndarray, np.ndarray]:
    # Same formula as hexbin_r_reference.R; integer products, then one division.
    k = np.arange(1, n + 1, dtype=np.float64)
    u = np.mod(k * 7919, 10007) / 10007
    v = np.mod(k * 104729, 10009) / 10009
    x = u * 10 - 5
    y = v * 6 - 3
    return x, y


def max_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        return math.inf
    if a.size == 0:
        return 0.0
    return float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64))))


def main() -> None:
    ref = load_reference(REF_PATH)
    n = len(ref[("points", "x")])
    x, y = points(n)
    report: list[str] = []
    report.append(f"points n={n}")

    # Points agree with R exactly.
    d = max(max_abs_diff(x, ref[("points", "x")]), max_abs_diff(y, ref[("points", "y")]))
    report.append(f"points (input formula) max abs diff vs R: {d:.3g}")

    # Grid dimensions as hexbin() computes them.
    xbins, shape = 30.0, 1.0
    jmax = math.floor(xbins + 1.5001)
    c1 = 2 * math.floor((xbins * shape) / math.sqrt(3) + 1.5001)
    imax = math.trunc((jmax * c1 - 1) / jmax + 1)
    dim_in = np.array([imax, jmax])
    report.append(
        f"dims max abs diff vs R: {max_abs_diff(dim_in, ref[('hbin', 'dim_in')]):.3g}"
    )

    xbnds = (float(x.min()), float(x.max()))
    ybnds = (float(y.min()), float(y.max()))

    results: dict[str, float] = {}

    # hbin: cells, counts, centroids, per-point ids, revised dim.
    cell, cnt, xcm, ycm, nrow, cell_ids = hexbin.hbin(
        x, y, xbins, shape, xbnds, ybnds, (imax, jmax), True
    )
    results["hbin cell"] = max_abs_diff(np.asarray(cell), ref[("hbin", "cell")])
    results["hbin cnt"] = max_abs_diff(np.asarray(cnt), ref[("hbin", "cnt")])
    results["hbin xcm"] = max_abs_diff(np.asarray(xcm), ref[("hbin", "xcm")])
    results["hbin ycm"] = max_abs_diff(np.asarray(ycm), ref[("hbin", "ycm")])
    results["hbin cell_ids"] = max_abs_diff(
        np.asarray(cell_ids), ref[("hbin", "cell_ids")]
    )
    results["hbin dim_out"] = abs(nrow - int(ref[("hbin", "dim_out")][0]))

    # hcell: per-point cell ids. R has no hcell entry point (reg.c registers only
    # hbin, herode, hsm), so the reference is R's per-point ids from hbin.
    hc_cell, hc_nrow = hexbin.hcell(x, y, xbins, shape, xbnds, ybnds, (imax, jmax))
    results["hcell cell (vs R hbin ids)"] = max_abs_diff(
        np.asarray(hc_cell), ref[("hbin", "cell_ids")]
    )

    # herode: inputs as R's erode.hexbin passes them; output is the erosion order.
    bdim = tuple(int(v) for v in ref[("herode", "bdim")])
    erode_out = hexbin.herode(
        ref[("herode", "in_cell")].astype(np.int32),
        ref[("herode", "in_cnt")].astype(np.int32),
        bdim,
    )
    results["herode erode"] = max_abs_diff(np.asarray(erode_out), ref[("herode", "erode")])

    # hsm: padded inputs as R's smooth.hexbin builds them, weights c(48, 4, 1).
    hsm_cell_out, hsm_cnt_out = hexbin.hsm(
        ref[("hsm", "in_cell")].astype(np.int32),
        ref[("hsm", "in_cnt")].astype(np.int32),
        int(ref[("hsm", "nmax")][0]),
        int(ref[("hsm", "ncol")][0]),
        tuple(int(v) for v in ref[("hsm", "wts")]),
    )
    results["hsm cell"] = max_abs_diff(np.asarray(hsm_cell_out), ref[("hsm", "out_cell")])
    results["hsm cnt"] = max_abs_diff(np.asarray(hsm_cnt_out), ref[("hsm", "out_cnt")])

    report.append("")
    report.append("max abs diff per output (tolerance 1e-8):")
    all_ok = True
    for name, diff in results.items():
        ok = diff <= TOL
        all_ok = all_ok and ok
        report.append(f"  {name:32s} {diff:.3g}  {'PASS' if ok else 'FAIL'}")
    report.append(f"overall: {'PASS' if all_ok else 'FAIL'}")

    # Timing: one representative hbin call, same points and grid as R.
    def call() -> None:
        hexbin.hbin(x, y, xbins, shape, xbnds, ybnds, (imax, jmax), True)

    call()  # untimed
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        call()
        times.append(time.perf_counter() - t0)
    py_median = statistics.median(times)

    r_median = None
    if R_TIMING_PATH.exists():
        for line in R_TIMING_PATH.read_text().splitlines():
            if line.startswith("R median seconds"):
                r_median = float(line.rsplit(":", 1)[1])
    report.append("")
    report.append("timing, one representative hbin call (median of 20 after one untimed call):")
    report.append(f"  Rust (hexbin.hbin, perf_counter) median seconds: {py_median:.9f}")
    if r_median is not None:
        report.append(f"  R (hexbin 1.28.6 .Fortran hbin, Sys.time) median seconds: {r_median:.9f}")
        report.append(f"  speedup (R / Rust): {r_median / py_median:.3f}")
    report.append(
        "  Rust timings (s): " + " ".join(f"{t:.6f}" for t in times)
    )

    text = "\n".join(report) + "\n"
    RESULT_PATH.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
