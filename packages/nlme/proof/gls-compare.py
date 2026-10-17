"""Run one R proof and its Python proof, then compare them.

Usage: python3 gls-compare.py <name>   (glsEstimate, glsApVar, gls, intervals, recalc-gls)

Expects proof/<name>-r.R and proof/<name>-py.py. Each prints one JSON line with
"value" (a flat list) and "median_ms" (median of 20 timed calls). Writes the raw
lines to docs/output/<name>-r.txt and docs/output/<name>-python.txt, then prints
matched (max abs diff <= 1e-8), max_abs_diff, R_ms, Python_ms, speedup = R / Python.
"""

import json
import subprocess
import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
OUTPUT = PROOF.parent / "docs" / "output"
TOLERANCE = 1e-8


def run(command: list[str]) -> dict:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
    return json.loads(lines[-1])


def main() -> None:
    name = sys.argv[1]
    r_result = run(["Rscript", str(PROOF / f"{name}-r.R")])
    py_result = run([sys.executable, str(PROOF / f"{name}-py.py")])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / f"{name}-r.txt").write_text(json.dumps(r_result) + "\n")
    (OUTPUT / f"{name}-python.txt").write_text(json.dumps(py_result) + "\n")

    r_value = r_result["value"]
    py_value = py_result["value"]
    if len(r_value) != len(py_value):
        print(f"{name}: length mismatch R={len(r_value)} Python={len(py_value)} matched=no")
        return
    max_diff = max((abs(a - b) for a, b in zip(r_value, py_value)), default=0.0)
    matched = max_diff <= TOLERANCE
    r_ms = r_result["median_ms"]
    py_ms = py_result["median_ms"]
    speedup = r_ms / py_ms if py_ms > 0 else float("inf")
    print(
        f"{name}: matched={'yes' if matched else 'no'} max_abs_diff={max_diff:.3g} "
        f"R_ms={r_ms:.4g} Python_ms={py_ms:.4g} speedup={speedup:.3g}"
    )


if __name__ == "__main__":
    main()
