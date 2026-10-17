"""R-vs-Python proofs for the nine requested lmom wrappers."""
from __future__ import annotations

import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "output"
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
from lmom.samlmu import samlmu
from lmom.samlmu_s import samlmu_s
from lmom._samlmu import _samlmu
from lmom.lmrp import lmrp
from lmom.lmrq import lmrq
from lmom.pelp import pelp
from lmom.pelq import pelq
from lmom.evdistp import evdistp
from lmom.evdistq import evdistq

R = OUT / "lmom_functions_r.txt"
RT = OUT / "lmom_functions_r_timings.txt"
P = OUT / "lmom_functions_python.txt"


def cases():
    x = np.array([-.7, .2, 1.1, 2.4, 3.0, 4.8])
    uniform_q = lambda p: p
    uniform_p = lambda x: np.clip(x, 0, 1)
    linear_q = lambda p, a: a[0] + a[1] * p
    linear_p = lambda x, a: np.clip((x - a[0]) / a[1], 0, 1)
    return {
        "samlmu": lambda: samlmu(x, 4, True, True),
        "samlmu.s": lambda: samlmu_s(x, 4, True, True),
        ".samlmu": lambda: _samlmu(x, 4),
        "lmrp": lambda: lmrp(uniform_p, bounds=(0, 1), order=4, ratios=True),
        "lmrq": lambda: lmrq(uniform_q, order=4, ratios=True),
        "pelp": lambda: pelp([.5, 1/6], linear_p, [0, 1], type="ls", bounds=(0, 1)),
        "pelq": lambda: pelq([.5, 1/6], linear_q, [0, 1], type="ls"),
        "evdistp": lambda: evdistp(linear_p, [0, 1], 11),
        "evdistq": lambda: evdistq(linear_q, [0, 1], 11),
    }


def flatten(value):
    return np.asarray(value, dtype=float).ravel()


def median_time(fn):
    fn()
    vals = []
    for _ in range(20):
        t0 = time.perf_counter()
        fn()
        vals.append(time.perf_counter() - t0)
    return statistics.median(vals)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["Rscript", str(HERE / "functions_proof.R"), str(R), str(RT)],
                   cwd=ROOT, check=True)
    rvals = [float(v) for v in R.read_text().split()]
    rtimes = [float(v) for v in RT.read_text().split()]
    funcs = cases()
    # R emits four values for each of the first seven cases and 22 for curves.
    python_values = []
    rows = []
    cursor = 0
    for index, (name, fn) in enumerate(funcs.items()):
        value = flatten(fn())
        python_values.extend(value)
        n = value.size
        rv = np.asarray(rvals[cursor:cursor+n])
        cursor += n
        diff = float(np.max(np.abs(value-rv)))
        r_ms = rtimes[index]
        py_ms = median_time(fn) * 1000
        rows.append((name, diff, r_ms, py_ms, r_ms / py_ms))
    P.write_text("\n".join(f"{v:.17g}" for v in python_values) + "\n")
    proof = OUT / "lmom_functions_proof.txt"
    lines = ["function max_abs_diff r_ms translated_ms speedup"]
    for name, diff, r_ms, py_ms, speedup in rows:
        lines.append(f"{name} {diff:.3e} {r_ms:.6g} {py_ms:.6g} {speedup:.6g}")
    lines.append("result: PASS" if all(d <= 1e-8 for _, d, _, _, _ in rows) else "result: FAIL")
    proof.write_text("\n".join(lines) + "\n")
    print(proof.read_text())


if __name__ == "__main__":
    main()
