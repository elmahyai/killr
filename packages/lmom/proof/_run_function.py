from __future__ import annotations

import importlib
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "packages" / "lmom"))
PARAMS = {
    "lmrexp": [1, 2], "lmrgam": [2.5, 1.5], "lmrgev": [0, 1, .2],
    "lmrglo": [0, 1, .3], "lmrgno": [0, 1, .2], "lmrgpa": [0, 1, .3],
    "lmrgum": [0, 1], "lmrkap": [0, 1, .2, .1], "lmrln3": [0, 0, 1],
    "lmrnor": [0, 1], "lmrpe3": [0, 1, .5], "lmrwak": [0, 1, .5, .2, .1],
    "lmrwei": [0, 1, 1],
}


def run(name: str) -> int:
    subprocess.run(["Rscript", str(HERE / "r_proof_function.R"), name],
                   cwd=ROOT, check=True)
    mod = importlib.import_module(f"lmom.{name}")
    fn = getattr(mod, name)
    nmom = 3 if name in {"lmrln3", "lmrwei"} else 4 if name in {"lmrgam", "lmrpe3"} else 5
    para = np.asarray(PARAMS[name], dtype=np.float64)
    value = np.asarray(fn(para, nmom=nmom), dtype=np.float64)
    (HERE / f"{name}_python_values.txt").write_text(
        "\n".join(f"{x:.17g}" for x in value) + "\n")
    fn(para, nmom=nmom)
    times = []
    for _ in range(20):
        start = time.perf_counter()
        fn(para, nmom=nmom)
        times.append(time.perf_counter() - start)
    py_time = float(np.median(times))
    r_time = float((HERE / f"{name}_r_time.txt").read_text())
    r_value = np.loadtxt(HERE / f"{name}_r_values.txt", ndmin=1)
    diff = float(np.max(np.abs(value - r_value)))
    matches = diff <= 1e-8
    report = (f"function: {name}\nmatch: {'yes' if matches else 'no'}\n"
              f"max_abs_diff: {diff:.17g}\nr_ms: {r_time*1000:.9g}\n"
              f"translated_ms: {py_time*1000:.9g}\n"
              f"speedup: {r_time/py_time:.9g}\n")
    (HERE / f"{name}_proof.txt").write_text(report)
    print(report, end="")
    return 0 if matches else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
