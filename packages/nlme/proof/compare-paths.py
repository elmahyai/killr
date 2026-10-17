"""Run the R and Python proofs for one nlme structure path and compare them.

Usage: <python> compare-paths.py [name ...]

Each name maps to one R script and one Python script in this folder. Both run
one untimed call and then 20 timed calls; the median of the 20 is the time.
Each side's JSON line is written to docs/output/<name>-r.txt and
docs/output/<name>-python.txt. The table gives matched (max abs diff within
1e-8), max_abs_diff, r_ms, translated_ms, and speedup = R time / Python time.
A path that does not match is reported as "no"; the tolerance is not loosened.
"""

import json
import subprocess
import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
OUTPUT = PROOF.parent / "docs" / "output"
PYTHON = PROOF.parents[2] / ".venv" / "bin" / "python"
TOLERANCE = 1e-8

# name -> (R script, Python script)
PAIRS = {
    "Initialize-corNatural": ("Initialize-corNatural-r.R", "Initialize-corNatural-py.py"),
    "Initialize-varExp": ("Initialize-varExp-r.R", "Initialize-varExp-py.py"),
    "logDet-corNatural": ("logDet-corNatural-r.R", "logDet-corNatural-py.py"),
    "recalc-corNatural": ("recalc-corNatural-r.R", "recalc-corNatural-py.py"),
    "recalc-corAR1": ("recalc-corAR1-r.R", "recalc-corAR1-py.py"),
    "Initialize-corAR1": ("Initialize-corAR1-r.R", "Initialize-corAR1-py.py"),
    "logDet-corAR1": ("logDet-corAR1-r.R", "logDet-corAR1-py.py"),
    "Initialize-corARMA": ("Initialize-corARMA-r.R", "Initialize-corARMA-py.py"),
    "logDet-corARMA": ("logDet-corARMA-r.R", "logDet-corARMA-py.py"),
    "recalc-corARMA": ("recalc-corARMA-r.R", "recalc-corARMA-py.py"),
    "Initialize-reStruct": ("Initialize-reStruct-r.R", "Initialize-reStruct-py.py"),
    "logDet-reStruct": ("logDet-reStruct-r.R", "logDet-reStruct-py.py"),
    "recalc-reStruct": ("recalc-reStruct-r.R", "recalc-reStruct-py.py"),
    "nlsList-selfStart": ("nlsList-selfStart-r.R", "nlsList-selfStart-py.py"),
    "nlme.nlsList-selfStart": ("nlme.nlsList-selfStart-r.R", "nlme.nlsList-selfStart-py.py"),
}


def run(command: list[str]) -> dict:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
    return json.loads(lines[-1])


def main() -> None:
    names = sys.argv[1:] or list(PAIRS)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    print("name | matched | max_abs_diff | r_ms | translated_ms | speedup")
    for name in names:
        r_script, py_script = PAIRS[name]
        r_result = run(["Rscript", str(PROOF / r_script)])
        py_result = run([str(PYTHON), str(PROOF / py_script)])
        (OUTPUT / f"{name}-r.txt").write_text(json.dumps(r_result) + "\n")
        (OUTPUT / f"{name}-python.txt").write_text(json.dumps(py_result) + "\n")
        r_value = r_result["value"]
        py_value = py_result["value"]
        if len(r_value) != len(py_value):
            print(f"{name} | no | length mismatch R={len(r_value)} Python={len(py_value)} | - | - | -")
            continue
        max_diff = max((abs(a - b) for a, b in zip(r_value, py_value)), default=0.0)
        matched = max_diff <= TOLERANCE
        r_ms = r_result["median_ms"]
        py_ms = py_result["median_ms"]
        speedup = r_ms / py_ms if py_ms > 0 else float("inf")
        print(
            f"{name} | {'yes' if matched else 'no'} | {max_diff:.3g} | {r_ms:.4g} | "
            f"{py_ms:.4g} | {speedup:.3g}"
        )


if __name__ == "__main__":
    main()
