"""Run the R and Python print.mclustBootstrapLRT proofs, compare, and record timings.

Outputs go to packages/mclust/docs/output/ and the summary to
packages/mclust/docs/print.mclustBootstrapLRT.json.
"""

import json
import subprocess
from pathlib import Path

ROOT = Path("/home/ahmed/killr_projects/killr/packages/mclust")
PROOF = ROOT / "proof"
OUT = ROOT / "docs" / "output"


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout, float(result.stderr.strip().splitlines()[-1])


r_text, r_ms = run(["Rscript", str(PROOF / "print.mclustBootstrapLRT-r.R")])
py_text, py_ms = run(["python3", str(PROOF / "print.mclustBootstrapLRT-py.py")])

(OUT / "print.mclustBootstrapLRT-r.txt").write_text(r_text)
(OUT / "print.mclustBootstrapLRT-py.txt").write_text(py_text)

matches = r_text == py_text
record = {
    "name": "print.mclustBootstrapLRT",
    "matches": matches,
    "max_abs_diff": 0.0 if matches else None,
    "max_abs_diff_note": "Text output compared byte for byte; no numeric output to diff.",
    "tolerance": 1e-8,
    "r_ms": r_ms,
    "translated_ms": py_ms,
    "speedup": r_ms / py_ms,
    "proof": {
        "r": "packages/mclust/proof/print.mclustBootstrapLRT-r.R",
        "python": "packages/mclust/proof/print.mclustBootstrapLRT-py.py",
    },
    "output": {
        "r": "packages/mclust/docs/output/print.mclustBootstrapLRT-r.txt",
        "python": "packages/mclust/docs/output/print.mclustBootstrapLRT-py.txt",
    },
}
(ROOT / "docs" / "print.mclustBootstrapLRT.json").write_text(
    json.dumps(record, indent=2) + "\n"
)
print(json.dumps(record, indent=2))
