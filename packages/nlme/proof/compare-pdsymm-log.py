"""Compare the pdSymm matrixLog_pd proof (R's .C routine vs nlme_pdsymm) and record timing.

Runs ``pdsymm-log-r.R`` and ``pdsymm-log-py.py``, saves both stdout streams under
``docs/output``, and reports the largest absolute difference over the factor and
the value (crossprod of the factor) for all cases. Matching means at most 1e-8.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
PROOF = PACKAGE / "proof"
OUTPUT = PACKAGE / "docs" / "output"
TOLERANCE = 1e-8
NAME = "pdsymm-log"


def run(command: list[str]) -> str:
    done = subprocess.run(command, check=True, capture_output=True, text=True)
    return done.stdout


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    r_text = run(["Rscript", str(PROOF / f"{NAME}-r.R")])
    py_text = run([sys.executable, str(PROOF / f"{NAME}-py.py")])
    (OUTPUT / f"{NAME}-r.txt").write_text(r_text)
    (OUTPUT / f"{NAME}-python.txt").write_text(py_text)
    r_value = json.loads(r_text)
    py_value = json.loads(py_text)
    r_vec = r_value["value"]
    py_vec = py_value["value"]
    if len(r_vec) != len(py_vec):
        raise SystemExit(f"length {len(py_vec)} differs from R {len(r_vec)}")
    max_diff = max(abs(a - b) for a, b in zip(r_vec, py_vec))
    summary = {
        NAME: {
            "matches": bool(max_diff <= TOLERANCE),
            "max_abs_diff": max_diff,
            "tolerance": TOLERANCE,
            "r_ms": r_value["median_ms"],
            "python_ms": py_value["median_ms"],
            "speedup": r_value["median_ms"] / py_value["median_ms"],
            "length": len(r_vec),
        }
    }
    (OUTPUT / f"{NAME}-compare.json").write_text(json.dumps(summary, indent=2) + "\n")
    row = summary[NAME]
    print(
        f"{NAME}: matches={row['matches']} max_abs_diff={row['max_abs_diff']:.3e} "
        f"r_ms={row['r_ms']:.3f} python_ms={row['python_ms']:.3f} speedup={row['speedup']:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
