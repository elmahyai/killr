"""Run the R and Python mclustBootstrapLRT proofs, compare them, and record timings.

Values are written to packages/mclust/docs/output/mclustBootstrapLRT-{r,py}.txt and the
median timings (ms) to mclustBootstrapLRT-{r,py}-time.txt. The summary goes to
packages/mclust/docs/output/mclustBootstrapLRT-compare.json.

Run with the project venv (python3 from .venv), since the Python proof imports the
mclust_kernels extension.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/ahmed/killr_projects/killr/packages/mclust")
PROOF = ROOT / "proof"
OUT = ROOT / "docs" / "output"
TOLERANCE = 1e-8
PY = sys.executable


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    values = [float(line) for line in lines[:-1]]
    return values, float(lines[-1])


r_values, r_ms = run(["Rscript", str(PROOF / "mclustBootstrapLRT-r.R")])
py_values, py_ms = run([PY, str(PROOF / "mclustBootstrapLRT-py.py")])

(OUT / "mclustBootstrapLRT-r.txt").write_text("\n".join("%.17g" % v for v in r_values) + "\n")
(OUT / "mclustBootstrapLRT-py.txt").write_text("\n".join("%.17g" % v for v in py_values) + "\n")
(OUT / "mclustBootstrapLRT-r-time.txt").write_text("%.17g\n" % r_ms)
(OUT / "mclustBootstrapLRT-py-time.txt").write_text("%.17g\n" % py_ms)


def split(values):
    default_len = int(values[0])
    return values[1:1 + default_len], values[1 + default_len:]


def diff(a, b):
    if len(a) != len(b):
        return float("inf"), False
    worst = max((abs(x - y) for x, y in zip(a, b)), default=0.0)
    return worst, worst <= TOLERANCE


r_default, r_small = split(r_values)
py_default, py_small = split(py_values)
dd, dd_ok = diff(r_default, py_default)
ds, ds_ok = diff(r_small, py_small)
max_abs = max(dd, ds)
matches = dd_ok and ds_ok

record = {
    "name": "mclustBootstrapLRT",
    "cran_version": "6.1.3",
    "matches": matches,
    "max_abs_diff": max_abs,
    "max_abs_diff_default_call": dd,
    "max_abs_diff_small_call": ds,
    "tolerance": TOLERANCE,
    "r_ms": r_ms,
    "translated_ms": py_ms,
    "speedup": r_ms / py_ms,
    "default_call": "mclustBootstrapLRT(data, modelName = \"EEE\") with nboot = 999, level = 0.05, maxG = NULL",
    "default_call_steps": len(r_default) // (3 + 999),
    "small_call": "mclustBootstrapLRT(data, modelName = \"EEE\", nboot = 15, maxG = 2) (compared, not timed)",
    "proof": {
        "r": "packages/mclust/proof/mclustBootstrapLRT-r.R",
        "python": "packages/mclust/proof/mclustBootstrapLRT-py.py",
        "compare": "packages/mclust/proof/mclustBootstrapLRT-compare.py",
    },
    "output": {
        "r": "packages/mclust/docs/output/mclustBootstrapLRT-r.txt",
        "python": "packages/mclust/docs/output/mclustBootstrapLRT-py.txt",
    },
}
(OUT / "mclustBootstrapLRT-compare.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
