from __future__ import annotations
import importlib, statistics, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "output"
CASES = {
    "cdfexp": [0, 2], "cdfgam": [2, 1.5], "cdfgev": [0, 1, .2],
    "cdfglo": [0, 1, -.3], "cdfgno": [0, 1, .2], "cdfgpa": [0, 1, .3],
    "cdfgum": [0, 1], "cdfkap": [0, 1, .2, .1], "cdfln3": [.5, 1, .2],
    "cdfnor": [0, 1], "cdfpe3": [0, 1, .5], "cdfwak": [0, 1, .5, .2, .1],
    "cdfwei": [0, 1.5, 2],
}
X = np.array([-2, -.5, 0, .5, 1, 2, 5, 10.], dtype=float)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    vals, timing = [], []
    for name, para in CASES.items():
        fn = getattr(importlib.import_module(f"lmom.{name}"), name)
        call = lambda: np.asarray(fn(X, para), dtype=float)
        call()
        ts = []
        for _ in range(20):
            t = time.perf_counter(); call(); ts.append(time.perf_counter() - t)
        value = call()
        vals.append(f"{name} " + " ".join(f"{v:.17g}" for v in value))
        timing.append(f"{name} {statistics.median(ts):.12g}")
    (OUT / "cdf_python_values.txt").write_text("\n".join(vals) + "\n")
    (OUT / "cdf_python_timings.txt").write_text("\n".join(timing) + "\n")
    rfile = OUT / "cdf_r_values.txt"
    rtimes = OUT / "cdf_r_timings.txt"
    summary = []
    if rfile.exists() and rtimes.exists():
        rv = {line.split()[0]: np.array([float(x) for x in line.split()[1:]]) for line in rfile.read_text().splitlines()}
        rt = {line.split()[0]: float(line.split()[1]) for line in rtimes.read_text().splitlines()}
        for name, _ in CASES.items():
            diff = float(np.max(np.abs(rv[name] - np.array([float(x) for x in vals[[v.split()[0] for v in vals].index(name)].split()[1:]]))))
            py = float(timing[[v.split()[0] for v in timing].index(name)].split()[1])
            summary.append(f"{name} {'yes' if diff <= 1e-8 else 'no'} {diff:.17g} {rt[name]*1000:.9g} {py*1000:.9g} {rt[name]/py:.9g}")
    else:
        summary = [f"{name} no nan nan nan nan (R proof unavailable)" for name in CASES]
    (OUT / "cdf_proof.txt").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))

if __name__ == "__main__":
    main()
