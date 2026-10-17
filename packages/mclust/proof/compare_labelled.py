"""Compare R and Python proof output for one function, label by label.

Usage: python compare_labelled.py <name>

Reads docs/output/<name>-r.txt and docs/output/<name>-python.txt. Each line is
"<label words> <values...>" (NA for missing, NULL for null). The line
"median_ms <value>" holds the median of 20 timed calls. Writes
docs/output/<name>-compare.txt with matches, max_abs_diff, r_ms,
translated_ms, and speedup (R time / Python time).

A label is the first two words when the line has a value after them, so
"A modelName X" has label "A modelName". The tolerance is 1e-8.
"""

import math
import sys
from pathlib import Path

TOL = 1e-8
root = Path(__file__).resolve().parents[1]
out_dir = root / "docs" / "output"
name = sys.argv[1]


def parse(path):
    labelled = {}
    median = None
    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "median_ms":
            median = float(parts[1])
            continue
        label, values = " ".join(parts[:2]), parts[2:]
        labelled[label] = values
    return labelled, median


def as_number(token):
    if token == "NA":
        return math.nan
    return float(token)


r_vals, r_ms = parse(out_dir / f"{name}-r.txt")
p_vals, py_ms = parse(out_dir / f"{name}-python.txt")

max_abs = 0.0
problems = []
for label, rv in r_vals.items():
    if label not in p_vals:
        problems.append(f"missing {label}")
        continue
    pv = p_vals[label]
    if len(rv) != len(pv):
        problems.append(f"length {label}: R {len(rv)} Python {len(pv)}")
        continue
    try:
        r_num = [as_number(t) for t in rv]
        p_num = [as_number(t) for t in pv]
    except ValueError:
        if rv != pv:
            problems.append(f"text {label}: R {rv} Python {pv}")
        continue
    for a, b in zip(r_num, p_num):
        if math.isnan(a) or math.isnan(b):
            if not (math.isnan(a) and math.isnan(b)):
                problems.append(f"NA mismatch {label}")
            continue
        max_abs = max(max_abs, abs(a - b))
for label in p_vals:
    if label not in r_vals:
        problems.append(f"extra {label}")

matches = not problems and max_abs <= TOL
speedup = r_ms / py_ms if r_ms and py_ms else float("nan")

lines = [
    f"matches: {'yes' if matches else 'no'}",
    f"max_abs_diff: {max_abs:.3g}",
    f"r_ms: {r_ms:.6g}",
    f"translated_ms: {py_ms:.6g}",
    f"speedup: {speedup:.4g}",
    f"labels_compared: {len(r_vals)}",
]
if problems:
    lines.append("problems:")
    lines += [f"  {p}" for p in problems]
text = "\n".join(lines) + "\n"
(out_dir / f"{name}-compare.txt").write_text(text)
print(text, end="")
