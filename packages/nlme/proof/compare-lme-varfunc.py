"""Compare the variance-function lme proof against R and record the timing.

Runs ``lme-varfunc-r.R`` with ``Rscript`` and ``lme-varfunc-py.py`` with this
interpreter, saves both stdout streams under ``docs/output``, and reports the
largest absolute difference for each variance class and quantity (fixef,
sigma, logLik, varFix, ranef, fitted, residuals). Matching means every quantity
is within 1e-8 and the nlminb call counts (iterations, function and gradient
evaluations) are equal for every class.
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

CLASSES = ("varPower", "varExp", "varIdent", "varConstPower", "varPower(~age|Sex)", "varExp(~age|Sex)")
# Index ranges inside one fit's block of values (R order), as in lme-family proofs.
PARTS = {
    "fixef": (0, 2),
    "sigma": (2, 3),
    "logLik": (3, 4),
    "varFix": (4, 8),
    "ranef": (8, 62),
    "fitted": (62, 278),
    "residuals": (278, 494),
}
BLOCK = 494


def run(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def last_json_line(text: str) -> dict:
    return json.loads([line for line in text.splitlines() if line.startswith("{")][-1])


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    r_text = run(["Rscript", str(PROOF / "lme-varfunc-r.R")])
    py_text = run([sys.executable, str(PROOF / "lme-varfunc-py.py")])
    (OUTPUT / "lme-varfunc-r.txt").write_text(r_text)
    (OUTPUT / "lme-varfunc-python.txt").write_text(py_text)
    r_value = last_json_line(r_text)
    py_value = last_json_line(py_text)
    r_vec = r_value["value"]
    py_vec = py_value["value"]
    if len(r_vec) != BLOCK * len(CLASSES) or len(py_vec) != len(r_vec):
        raise SystemExit(f"unexpected value lengths: R {len(r_vec)}, Python {len(py_vec)}")

    per_class = {}
    for index, name in enumerate(CLASSES):
        start = index * BLOCK
        by_part = {
            part: max(
                abs(a - b)
                for a, b in zip(r_vec[start + lo : start + hi], py_vec[start + lo : start + hi])
            )
            for part, (lo, hi) in PARTS.items()
        }
        iterations_equal = r_value["iterations"][index] == py_value["iterations"][index]
        max_diff = max(by_part.values())
        per_class[name] = {
            "matches": bool(max_diff <= TOLERANCE and iterations_equal),
            "max_abs_diff": max_diff,
            "max_abs_diff_by_quantity": by_part,
            "iterations_r": r_value["iterations"][index],
            "iterations_python": py_value["iterations"][index],
            "iterations_equal": bool(iterations_equal),
        }

    overall = max(row["max_abs_diff"] for row in per_class.values())
    summary = {
        "matches": all(row["matches"] for row in per_class.values()),
        "max_abs_diff": overall,
        "tolerance": TOLERANCE,
        "classes": per_class,
        "r_ms": r_value["median_ms"],
        "python_ms": py_value["median_ms"],
        "speedup": r_value["median_ms"] / py_value["median_ms"],
        "length": len(r_vec),
    }
    (OUTPUT / "lme-varfunc-compare.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"lme varfunc: matches={summary['matches']} max_abs_diff={overall:.3e} "
        f"r_ms={summary['r_ms']:.3f} python_ms={summary['python_ms']:.3f} "
        f"speedup={summary['speedup']:.2f}"
    )
    for name, row in per_class.items():
        print(
            f"  {name}: matches={row['matches']} max_abs_diff={row['max_abs_diff']:.3e} "
            f"iterations_equal={row['iterations_equal']} "
            f"iterations_r={row['iterations_r']} iterations_python={row['iterations_python']}"
        )
        for part, diff in row["max_abs_diff_by_quantity"].items():
            print(f"      {part}: {diff:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
