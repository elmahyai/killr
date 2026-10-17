"""Proof, Python side for ecme(). Runs packages/pan/pan/ecme.py on the five cases of
ecme_r.R, times them, and compares every output with the R output in
docs/output/r_ecme.txt.

Usage (run ecme_r.R first):
    python3 packages/pan/proof/ecme_py.py

Each case: one untimed call, then the median of 20 timed calls (time.perf_counter()).
The headline ecme time is the sum of the five case medians, for R and for Python.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PKG = HERE.parent  # packages/pan, which holds the pan/ package
FIX = HERE / "fixture"
OUT = HERE.parent / "docs" / "output"
sys.path.insert(0, str(PKG))

from pan.ecme import ecme  # noqa: E402

TOL = 1e-8
ITEMS = ["beta", "sigma2", "psi", "converged", "iter", "loglik", "cov.beta", "bhat", "cov.b"]
KEY = {"cov.beta": "cov_beta", "cov.b": "cov_b"}


def load_inputs():
    subj = np.loadtxt(FIX / "subj.csv", dtype=np.int64, ndmin=1)
    pred = np.loadtxt(FIX / "pred.csv", delimiter=",", ndmin=2)
    y = np.loadtxt(FIX / "ecme_y.csv", ndmin=1)
    occ = np.loadtxt(FIX / "ecme_occ.csv", dtype=np.int64, ndmin=1)
    vmax = np.loadtxt(FIX / "ecme_vmax.csv", delimiter=",", ndmin=2)
    return subj, pred, y, occ, vmax


def read_r(path):
    """Parses ecme_r.R output into {case: {"items": {name: None | (dims, values)}, "median": s}}."""
    res = {}
    case = None
    lines = path.read_text().splitlines()
    i = 0
    while i < len(lines):
        parts = lines[i].split()
        tag = parts[0]
        if tag == "CASE":
            case = parts[1]
            res[case] = {"items": {}, "median": None}
            i += 1
        elif tag == "BLOCK":
            name = parts[1]
            dims = tuple(int(d) for d in parts[2].split(","))
            n = int(np.prod(dims))
            vals = np.array([float(v) for v in lines[i + 1 : i + 1 + n]])
            res[case]["items"][name] = (dims, vals)
            i += 1 + n
        elif tag == "NULL":
            res[case]["items"][parts[1]] = None
            i += 1
        elif tag == "MEDIAN":
            res[case]["median"] = float(parts[1])
            i += 1
        else:
            i += 1
    return res


def cases(subj, pred, y, occ, vmax):
    """The five cases, in the same order and with the same arguments as ecme_r.R."""
    base = dict(y=y, subj=subj, occ=occ, pred=pred, xcol=[1, 2, 3])
    start = dict(beta=np.array([1.0, 0.5, 0.3]), sigma2=1.0,
                 psi=np.array([[0.5, 0.1], [0.1, 0.5]]))
    return {
        "A": dict(base, zcol=None),
        "B": dict(base, zcol=None, vmax=vmax),
        "C": dict(base, zcol=[1, 2], random_effects=True),
        "D": dict(base, zcol=[1, 2], vmax=vmax),
        "E": dict(base, zcol=[1, 2], start=start),
    }


def as_flat(value):
    """A Python output as the values R writes: column-major, with its dimensions."""
    arr = np.asarray(value, dtype=float)
    dims = arr.shape if arr.ndim > 0 else (1,)
    return dims, arr.reshape(-1, order="F")


def main():
    subj, pred, y, occ, vmax = load_inputs()
    r_res = read_r(OUT / "r_ecme.txt")
    lines = ["Proof: ecme (Python port of the ECME loop) vs R pan 2.0 ecme on the fixed fixture "
             f"(ntot {y.size}, m {np.unique(subj).size}, tol {TOL:g})"]
    all_ok = True
    py_out = []
    r_total = 0.0
    py_total = 0.0
    for case, kwargs in cases(subj, pred, y, occ, vmax).items():
        out = ecme(**kwargs)  # untimed call
        times = []
        for _ in range(20):
            t0 = time.perf_counter()
            ecme(**kwargs)
            times.append(time.perf_counter() - t0)
        py_med = float(statistics.median(times))
        r_med = r_res[case]["median"]
        r_total += r_med
        py_total += py_med

        case_ok = True
        worst = 0.0
        parts = []
        for name in ITEMS:
            rv = r_res[case]["items"][name]
            pv = out[KEY.get(name, name)]
            if rv is None:
                ok = pv is None
                parts.append(f"{name}=NULL {'ok' if ok else 'MISMATCH'}")
            elif pv is None:
                ok = False
                parts.append(f"{name} MISSING")
            else:
                dims, rvals = rv
                if name == "converged":
                    pv = float(bool(pv))
                pdims, pvals = as_flat(pv)
                if int(np.prod(pdims)) != rvals.size:
                    ok = False
                    diff = float("inf")
                else:
                    diff = float(np.max(np.abs(pvals - rvals))) if rvals.size else 0.0
                    ok = diff <= TOL
                worst = max(worst, diff)
                parts.append(f"{name} max_abs_diff={diff:.3e}")
            case_ok = case_ok and ok
        all_ok = all_ok and case_ok
        lines.append(f"case {case} ({'PASS' if case_ok else 'FAIL'}): " + "; ".join(parts))
        lines.append(f"case {case} R attempts before a clean call: {r_res_attempts(case)}; "
                     f"R median {r_med:.6f} s; Python median {py_med:.6f} s; "
                     f"speedup {r_med / py_med:.2f}")
        py_out.append((case, out, times))

    lines.append(f"Result: {'PASS' if all_ok else 'FAIL'} (tolerance {TOL:g})")
    lines.append(f"ecme total, sum of the five case medians: R {r_total:.6f} s, "
                 f"Python {py_total:.6f} s, speedup (R / Python) = {r_total / py_total:.2f}")
    text = "\n".join(lines) + "\n"
    print(text, end="")
    (OUT / "ecme_compare.txt").write_text(text)

    with open(OUT / "py_ecme.txt", "w") as fh:
        for case, out, times in py_out:
            fh.write(f"CASE {case}\n")
            for name in ITEMS:
                v = out[KEY.get(name, name)]
                if v is None:
                    fh.write(f"NULL {name}\n")
                    continue
                if name == "converged":
                    v = float(bool(v))
                dims, vals = as_flat(v)
                fh.write(f"BLOCK {name} {','.join(str(d) for d in dims)}\n")
                fh.write("".join(f"{x:.17g}\n" for x in vals))
            fh.write("TIMES " + " ".join(f"{t:.9g}" for t in times) + "\n")
            fh.write(f"MEDIAN {statistics.median(times):.9g}\n")

    if not all_ok:
        sys.exit(1)


def r_res_attempts(case):
    text = (OUT / "r_ecme.txt").read_text().splitlines()
    seen = False
    for line in text:
        if line == f"CASE {case}":
            seen = True
        elif seen and line.startswith("ATTEMPTS"):
            return line.split()[1]
    return "?"


if __name__ == "__main__":
    main()
