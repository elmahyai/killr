import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "proof"
OUT = ROOT / "docs" / "output"
TOLERANCE = 1e-8


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    return np.asarray([float(v) for v in lines[:-1]]), float(lines[-1])


r_values, r_ms = run(["Rscript", str(PROOF / "plot.mclustBootstrapLRT-r.R")])
py_values, py_ms = run([sys.executable, str(PROOF / "plot.mclustBootstrapLRT-py.py")])
max_abs = float(np.max(np.abs(r_values - py_values)))
record = {
    "name": "plot.mclustBootstrapLRT",
    "cran_version": "6.1.3",
    "matches": bool(max_abs <= TOLERANCE),
    "max_abs_diff": max_abs,
    "tolerance": TOLERANCE,
    "r_ms": r_ms,
    "translated_ms": py_ms,
    "speedup": r_ms / py_ms,
    "proof": {
        "r": "packages/mclust/proof/plot.mclustBootstrapLRT-r.R",
        "python": "packages/mclust/proof/plot.mclustBootstrapLRT-py.py",
        "compare": "packages/mclust/proof/plot.mclustBootstrapLRT-compare.py",
    },
    "output": {
        "r": "packages/mclust/docs/output/plot.mclustBootstrapLRT-r.txt",
        "python": "packages/mclust/docs/output/plot.mclustBootstrapLRT-py.txt",
        "figure": "packages/mclust/docs/output/plot.mclustBootstrapLRT-python.svg",
    },
}
(OUT / "plot.mclustBootstrapLRT-r.txt").write_text("\n".join("%.17g" % v for v in r_values) + "\n")
(OUT / "plot.mclustBootstrapLRT-py.txt").write_text("\n".join("%.17g" % v for v in py_values) + "\n")
(OUT / "plot.mclustBootstrapLRT-compare.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
