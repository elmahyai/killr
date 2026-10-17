"""Run nlsList-nostart-r.R and nlsList-nostart-py.py and compare the four cases.

A case matches when every coefficient, residual standard error, and convergence flag agrees
with R within 1e-8. Timings come from the two runs (median of 20 timed calls each).
Writes docs/output/nlsList-nostart-compare.txt and prints the summary as JSON.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOLERANCE = 1e-8


def run_json(command):
    completed = subprocess.run(command, cwd=HERE, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout.strip().splitlines()[-1])


def main():
    r_cases = {c["name"]: c for c in run_json(["Rscript", "nlsList-nostart-r.R"])["cases"]}
    py_cases = {c["name"]: c for c in run_json([sys.executable, "nlsList-nostart-py.py"])["cases"]}
    summary = []
    for name, r_case in r_cases.items():
        py_case = py_cases[name]
        r_value = np.asarray(r_case["value"], dtype=np.float64)
        py_value = np.asarray(py_case["value"], dtype=np.float64)
        if r_value.shape != py_value.shape:
            raise SystemExit(f"{name}: value lengths differ")
        # Layout per group: Asym, lrc, c0, sigma, converged (1 or 0).
        flags = np.arange(r_value.size) % 5 == 4
        diff = np.abs(r_value - py_value)
        numeric_ok = bool(np.all(diff[~flags] <= TOLERANCE))
        flags_ok = bool(np.array_equal(r_value[flags], py_value[flags]))
        r_ms = r_case["median_ms"]
        py_ms = py_case["median_ms"]
        summary.append(
            {
                "case": name,
                "matches": numeric_ok and flags_ok,
                "max_abs_diff": float(diff[~flags].max()),
                "convergence_flags_match": flags_ok,
                "groups": int(r_value.size // 5),
                "r_ms": r_ms,
                "translated_ms": py_ms,
                "speedup": r_ms / py_ms,
            }
        )
    lines = ["nlsList no-start and with-start cases against R (nlme 3.1-171)", ""]
    for item in summary:
        lines.append(
            f"{item['case']}: matches={'yes' if item['matches'] else 'no'} "
            f"max_abs_diff={item['max_abs_diff']:.3g} groups={item['groups']} "
            f"convergence_flags_match={'yes' if item['convergence_flags_match'] else 'no'} "
            f"r_ms={item['r_ms']:.3f} translated_ms={item['translated_ms']:.3f} "
            f"speedup={item['speedup']:.3f}"
        )
    out_dir = ROOT / "docs" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "nlsList-nostart-compare.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"tolerance": TOLERANCE, "cases": summary}, indent=1))


if __name__ == "__main__":
    main()
