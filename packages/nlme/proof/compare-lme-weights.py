"""Compare the weighted ``lme`` proof (varFixed(~invwt)) against R and record the timing.

Runs ``lme-weights-r.R`` with ``Rscript`` and ``lme-weights-py.py`` with this
interpreter, saves both stdout streams under ``docs/output``, and reports the
largest absolute difference for each quantity (fixef, sigma, logLik, varFix,
ranef, fitted, residuals). Matching means every quantity is within 1e-8 and the
nlminb call counts are equal.
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

PARTS = {
    "fixef": (0, 2),
    "sigma": (2, 3),
    "logLik": (3, 4),
    "varFix": (4, 8),
    "ranef": (8, 62),
    "fitted": (62, 278),
    "residuals": (278, 494),
}


def run(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def last_json_line(text: str) -> dict:
    return json.loads([line for line in text.splitlines() if line.startswith("{")][-1])


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    r_text = run(["Rscript", str(PROOF / "lme-weights-r.R")])
    py_text = run([sys.executable, str(PROOF / "lme-weights-py.py")])
    (OUTPUT / "lme-weights-r.txt").write_text(r_text)
    (OUTPUT / "lme-weights-python.txt").write_text(py_text)
    r_value = last_json_line(r_text)
    py_value = last_json_line(py_text)
    by_part = {
        part: max(abs(a - b) for a, b in zip(r_value["value"][start:stop], py_value["value"][start:stop]))
        for part, (start, stop) in PARTS.items()
    }
    max_diff = max(by_part.values())
    iterations_equal = r_value["iterations"] == py_value["iterations"]
    summary = {
        "matches": bool(max_diff <= TOLERANCE and iterations_equal),
        "max_abs_diff": max_diff,
        "max_abs_diff_by_quantity": by_part,
        "tolerance": TOLERANCE,
        "iterations_r": r_value["iterations"],
        "iterations_python": py_value["iterations"],
        "iterations_equal": bool(iterations_equal),
        "r_ms": r_value["median_ms"],
        "python_ms": py_value["median_ms"],
        "speedup": r_value["median_ms"] / py_value["median_ms"],
        "length": len(r_value["value"]),
    }
    (OUTPUT / "lme-weights-compare.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"lme weights: matches={summary['matches']} max_abs_diff={max_diff:.3e} "
        f"iterations_equal={iterations_equal} r_ms={summary['r_ms']:.3f} "
        f"python_ms={summary['python_ms']:.3f} speedup={summary['speedup']:.2f}"
    )
    for part, diff in by_part.items():
        print(f"    {part}: {diff:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
