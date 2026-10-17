"""Run the per-class coverage proofs for nlme Initialize, logDet and recalc, and compare them with R.

Usage: python3 coverage-compare.py [class ...]

With no arguments every class is run. Each class has one R script
``<class>-coverage-r.R`` and one Python script ``<class>-coverage-py.py`` in this folder.
Both print one JSON line with the entries "Initialize", "logDet" and "recalc"; each entry
has the values and the median of 20 timed calls (after one untimed call), or an error.

Writes, per class, docs/output/<class>-coverage-r.txt and
docs/output/<class>-coverage-python.txt (the raw JSON lines), and a table to
docs/output/coverage-summary.txt. ``matches`` is yes when the max abs difference is within
1e-8. ``speedup`` is the R median time divided by the Python median time.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
OUTPUT = PROOF.parent / "docs" / "output"
TOLERANCE = 1e-8
VENV_PYTHON = PROOF.parents[2] / ".venv" / "bin" / "python"
FUNCTIONS = ("Initialize", "logDet", "recalc")

# class name -> file stem of the proof pair
CLASSES = {
    "corLin": "corLin",
    "corRatio": "corRatio",
    "corSpher": "corSpher",
    "corExp": "corExp",
    "corGaus": "corGaus",
    "corSpatial": "corSpatial",
    "corCAR1": "corCAR1",
    "corSymm": "corSymm",
    "corAR1 (non-consecutive, corARMA path)": "corAR1-noncons",
    "pdSymm": "pdSymm",
    "pdDiag": "pdDiag",
    "pdIdent": "pdIdent",
    "pdCompSymm": "pdCompSymm",
}


def python_exe() -> str:
    return str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def run_json(command: list[str]) -> dict:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
    if not lines:
        return {f: {"error": f"no JSON output (exit {completed.returncode}): {completed.stderr[-300:]}"} for f in FUNCTIONS}
    return json.loads(lines[-1])


def compare(r_entry: dict, py_entry: dict) -> tuple[str, str, str, str]:
    """Return (matches, max_abs_diff, speedup, note) for one function."""
    if "error" in r_entry:
        return "no", "-", "-", f"R error: {r_entry['error']}"
    if "error" in py_entry:
        return "no", "-", "-", f"not translated: {py_entry['error']}"
    r_value, py_value = r_entry["value"], py_entry["value"]
    if len(r_value) != len(py_value) or not r_value:
        return "no", "-", "-", f"length mismatch R={len(r_value)} Python={len(py_value)}"
    max_diff = max(abs(a - b) for a, b in zip(r_value, py_value))
    matched = max_diff <= TOLERANCE
    r_ms, py_ms = r_entry["median_ms"], py_entry["median_ms"]
    speedup = r_ms / py_ms if py_ms > 0 else float("inf")
    return ("yes" if matched else "no"), f"{max_diff:.3g}", f"{speedup:.3g}", ""


def main() -> None:
    names = sys.argv[1:] or list(CLASSES)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows: list[str] = []
    header = "class | function | matches | max_abs_diff | speedup (R/Python) | note | proof R | proof Python"
    rows.append(header)
    for label in names:
        stem = CLASSES.get(label, label)
        r_script = PROOF / f"{stem}-coverage-r.R"
        py_script = PROOF / f"{stem}-coverage-py.py"
        r_result = run_json(["Rscript", str(r_script)])
        py_result = run_json([python_exe(), str(py_script)])
        (OUTPUT / f"{stem}-coverage-r.txt").write_text(json.dumps(r_result) + "\n")
        (OUTPUT / f"{stem}-coverage-python.txt").write_text(json.dumps(py_result) + "\n")
        for function in FUNCTIONS:
            matches, diff, speedup, note = compare(
                r_result.get(function, {"error": "missing"}), py_result.get(function, {"error": "missing"})
            )
            rel_r = r_script.relative_to(PROOF.parent)
            rel_py = py_script.relative_to(PROOF.parent)
            rows.append(
                f"{label} | {function} | {matches} | {diff} | {speedup} | {note} | {rel_r} | {rel_py}"
            )
            print(rows[-1])
    (OUTPUT / "coverage-summary.txt").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
