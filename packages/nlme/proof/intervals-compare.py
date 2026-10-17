"""Run the R and Python intervals proofs for both paths and compare them.

Usage: <python> intervals-compare.py

Paths: no apVar (Orthodont gls, intervals-r.R / intervals-py.py) and apVar
(Oats gls with corAR1, intervals-apvar-r.R / intervals-apvar-py.py). Each side's
JSON line is written to docs/output/. The table gives matched (max abs diff within
1e-8), max_abs_diff, r_ms, translated_ms, and speedup = R time / Python time.
"""

import json
import subprocess
import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
OUTPUT = PROOF.parent / "docs" / "output"
TOLERANCE = 1e-8

# name -> (R script, Python script, output stem)
PAIRS = {
    "intervals (no apVar)": ("intervals-r.R", "intervals-py.py", "intervals"),
    "intervals (apVar)": ("intervals-apvar-r.R", "intervals-apvar-py.py", "intervals-apVar"),
}


def run(command: list[str]) -> dict:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
    return json.loads(lines[-1])


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    print("case | matched | max_abs_diff | r_ms | translated_ms | speedup")
    for label, (r_script, py_script, stem) in PAIRS.items():
        r_result = run(["Rscript", str(PROOF / r_script)])
        py_result = run([sys.executable, str(PROOF / py_script)])
        (OUTPUT / f"{stem}-r.txt").write_text(json.dumps(r_result) + "\n")
        (OUTPUT / f"{stem}-python.txt").write_text(json.dumps(py_result) + "\n")
        r_value = r_result["value"]
        py_value = py_result["value"]
        if len(r_value) != len(py_value):
            print(f"{label} | no | length mismatch R={len(r_value)} Python={len(py_value)} | - | - | -")
            continue
        max_diff = max((abs(a - b) for a, b in zip(r_value, py_value)), default=0.0)
        matched = max_diff <= TOLERANCE
        r_ms = r_result["median_ms"]
        py_ms = py_result["median_ms"]
        speedup = r_ms / py_ms if py_ms > 0 else float("inf")
        print(
            f"{label} | {'yes' if matched else 'no'} | {max_diff:.3g} | {r_ms:.4g} | "
            f"{py_ms:.4g} | {speedup:.3g}"
        )


if __name__ == "__main__":
    main()
