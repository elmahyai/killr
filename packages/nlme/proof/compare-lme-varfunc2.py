"""Compare the newly supported lme variance-function cases against R and record the timing.

Runs ``lme-varfunc2-r.R`` with ``Rscript`` and ``lme-varfunc2-py.py`` with this
interpreter, saves both stdout streams under ``docs/output``, and reports the
largest absolute difference for each case and quantity. A case matches when every
quantity is within 1e-8 and every nlminb call (iterations, function and gradient
evaluations) is equal in order. The apVar case has 25 extra values (the apVar
matrix, column-major) after the common block.
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

CASES = ("varPowerFixed", "varExpFixed", "varPowerFitted", "varExpFitted", "varConstPowerFitted", "varPowerApVar")
# Index ranges inside one case's block of values (R order), as in lme-varfunc-compare.py.
PARTS = {
    "fixef": (0, 2),
    "sigma": (2, 3),
    "logLik": (3, 4),
    "varFix": (4, 8),
    "ranef": (8, 62),
    "fitted": (62, 278),
    "residuals": (278, 494),
    "apVar": (494, 519),
}


def run(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def last_json_line(text: str) -> dict:
    return json.loads([line for line in text.splitlines() if line.startswith("{")][-1])


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    r_text = run(["Rscript", str(PROOF / "lme-varfunc2-r.R")])
    py_text = run([sys.executable, str(PROOF / "lme-varfunc2-py.py")])
    (OUTPUT / "lme-varfunc2-r.txt").write_text(r_text)
    (OUTPUT / "lme-varfunc2-python.txt").write_text(py_text)
    r_value = last_json_line(r_text)
    py_value = last_json_line(py_text)
    r_vec = r_value["value"]
    py_vec = py_value["value"]
    if r_value["lengths"] != py_value["lengths"] or len(r_vec) != len(py_vec):
        raise SystemExit(f"layout mismatch: R {r_value['lengths']}, Python {py_value['lengths']}")

    per_case = {}
    offset = 0
    for name, length in zip(CASES, r_value["lengths"]):
        by_part = {}
        for part, (lo, hi) in PARTS.items():
            if hi > length:
                continue
            by_part[part] = max(
                abs(a - b) for a, b in zip(r_vec[offset + lo : offset + hi], py_vec[offset + lo : offset + hi])
            )
        iterations_equal = r_value["iterations"][CASES.index(name)] == py_value["iterations"][CASES.index(name)]
        max_diff = max(by_part.values())
        per_case[name] = {
            "matches": bool(max_diff <= TOLERANCE and iterations_equal),
            "max_abs_diff": max_diff,
            "max_abs_diff_by_quantity": by_part,
            "nlminb_calls_r": len(r_value["iterations"][CASES.index(name)]),
            "nlminb_calls_python": len(py_value["iterations"][CASES.index(name)]),
            "iterations_equal": bool(iterations_equal),
        }
        offset += length

    overall = max(row["max_abs_diff"] for row in per_case.values())
    summary = {
        "matches": all(row["matches"] for row in per_case.values()),
        "max_abs_diff": overall,
        "tolerance": TOLERANCE,
        "cases": per_case,
        "r_ms": r_value["median_ms"],
        "python_ms": py_value["median_ms"],
        "speedup": r_value["median_ms"] / py_value["median_ms"],
        "lengths": r_value["lengths"],
    }
    (OUTPUT / "lme-varfunc2-compare.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"lme varfunc2: matches={summary['matches']} max_abs_diff={overall:.3e} "
        f"r_ms={summary['r_ms']:.3f} python_ms={summary['python_ms']:.3f} "
        f"speedup={summary['speedup']:.2f}"
    )
    for name, row in per_case.items():
        print(
            f"  {name}: matches={row['matches']} max_abs_diff={row['max_abs_diff']:.3e} "
            f"iterations_equal={row['iterations_equal']} "
            f"nlminb_calls_r={row['nlminb_calls_r']} nlminb_calls_python={row['nlminb_calls_python']}"
        )
        for part, diff in row["max_abs_diff_by_quantity"].items():
            print(f"      {part}: {diff:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
