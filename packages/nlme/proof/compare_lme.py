"""Compare the lme-family proofs against R and record the timing.

Runs each R proof (``Rscript``) and each Python proof with the same
interpreter, saves both stdout streams under ``docs/output``, and reports
the largest absolute difference for each returned quantity (fixed effects,
sigma, logLik, varFix, ranef, fitted, residuals, or the anova columns).
It also compares the ``nlminb`` call counts (iterations, function and
gradient evaluations) recorded by each proof. Matching means every quantity
is within 1e-8 and the call counts are equal.
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

# Index ranges into the value vector each proof returns (R order).
LME_PARTS = {
    "fixef": (0, 2),
    "sigma": (2, 3),
    "logLik": (3, 4),
    "varFix": (4, 8),
    "ranef": (8, 62),
    "fitted": (62, 278),
    "residuals": (278, 494),
}
ANOVA_PARTS = {
    "numDF": (0, 2),
    "denDF": (2, 4),
    "F-value": (4, 6),
    "p-value": (6, 8),
}
FUNCTIONS = {
    "lme": LME_PARTS,
    "lme.formula": LME_PARTS,
    "lme.lmList": LME_PARTS,
    "anova.lme": ANOVA_PARTS,
}


def run(command: list[str]) -> str:
    done = subprocess.run(command, check=True, capture_output=True, text=True)
    return done.stdout


def last_json_line(text: str) -> dict:
    lines = [line for line in text.splitlines() if line.startswith("{")]
    return json.loads(lines[-1])


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, parts in FUNCTIONS.items():
        r_text = run(["Rscript", str(PROOF / f"{name}-r.R")])
        py_text = run([sys.executable, str(PROOF / f"{name}-py.py")])
        (OUTPUT / f"{name}-r.txt").write_text(r_text)
        (OUTPUT / f"{name}-python.txt").write_text(py_text)
        r_value = last_json_line(r_text)
        py_value = last_json_line(py_text)
        r_vec = r_value["value"]
        py_vec = py_value["value"]
        if len(r_vec) != len(py_vec):
            raise SystemExit(f"{name}: length {len(py_vec)} differs from R {len(r_vec)}")
        by_part = {}
        for part, (start, stop) in parts.items():
            by_part[part] = max(abs(a - b) for a, b in zip(r_vec[start:stop], py_vec[start:stop]))
        max_diff = max(by_part.values())
        r_iter = r_value["iterations"]
        py_iter = py_value["iterations"]
        r_ms = r_value["median_ms"]
        py_ms = py_value["median_ms"]
        summary[name] = {
            "matches": bool(max_diff <= TOLERANCE and r_iter == py_iter),
            "max_abs_diff": max_diff,
            "max_abs_diff_by_quantity": by_part,
            "tolerance": TOLERANCE,
            "iterations_r": r_iter,
            "iterations_python": py_iter,
            "iterations_equal": bool(r_iter == py_iter),
            "r_ms": r_ms,
            "python_ms": py_ms,
            "speedup": r_ms / py_ms,
            "length": len(r_vec),
        }
    (OUTPUT / "lme-family-compare.json").write_text(json.dumps(summary, indent=2) + "\n")
    for name, row in summary.items():
        print(
            f"{name}: matches={row['matches']} max_abs_diff={row['max_abs_diff']:.3e} "
            f"iterations_equal={row['iterations_equal']} "
            f"r_ms={row['r_ms']:.3f} python_ms={row['python_ms']:.3f} speedup={row['speedup']:.2f}"
        )
        for part, diff in row["max_abs_diff_by_quantity"].items():
            print(f"    {part}: {diff:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
