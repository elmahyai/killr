"""Compare the R and Python estep proof outputs and write the summary.

Each output file holds one value per line, then the median time in milliseconds
on the last line. Values match when both are NaN, both are the same infinity, or
the absolute difference is at most 1e-8. A NaN on one side only is a mismatch.
"""

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs" / "output"
TOL = 1e-8


def read(name):
    lines = [line.strip() for line in (ROOT / name).read_text().splitlines() if line.strip()]
    values = [float(x) for x in lines[:-1]]
    return values, float(lines[-1])


r_values, r_ms = read("estep-r.txt")
py_values, py_ms = read("estep-python.txt")

matches = len(r_values) == len(py_values)
max_abs_diff = 0.0
if matches:
    for a, b in zip(r_values, py_values):
        if math.isnan(a) or math.isnan(b):
            if math.isnan(a) != math.isnan(b):
                matches = False
            continue
        if math.isinf(a) or math.isinf(b):
            if a != b:
                matches = False
            continue
        diff = abs(a - b)
        max_abs_diff = max(max_abs_diff, diff)
        if diff > TOL:
            matches = False

speedup = r_ms / py_ms
text = "\n".join(
    [
        "estep",
        f"matches: {'true' if matches else 'false'}",
        f"max_abs_diff: {max_abs_diff:.6e}",
        f"values: {len(r_values)}",
        f"r_ms: {r_ms:.6g}",
        f"translated_ms: {py_ms:.6g}",
        f"speedup: {speedup:.4g}",
        "",
    ]
)
(ROOT / "estep-compare.txt").write_text(text)
print(text)
