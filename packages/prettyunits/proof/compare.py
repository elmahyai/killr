"""Compare the R and Python proof outputs for every prettyunits export.

Reads docs/output/<name>-r.txt and docs/output/<name>-python.txt, checks that
the results match within 1e-8 (numbers) or exactly (strings, booleans, NA,
NaN, Inf, and the error marker), and prints one row per function. The same
rows are written to docs/output/summary.txt.

A length-one R vector is written as a scalar, and a Python one-element list
for the same value is accepted; the element is compared.
"""

import json
import math
import sys
from pathlib import Path

PROOF_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROOF_DIR.parent / "docs" / "output"
TOLERANCE = 1e-8

FUNCTIONS = [
    "compute_bytes", "compute_num", "pretty_bytes", "pretty_color", "pretty_colour",
    "pretty_dt", "pretty_ms", "pretty_num", "pretty_p_value", "pretty_round",
    "pretty_sec", "pretty_signif", "time_ago", "vague_dt",
]


def read_output(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    median_ms = float(lines[0].split()[1])
    result = json.loads(lines[1][len("result "):])
    return median_ms, result


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _compare(a, b, found):
    """Return True when a and b agree. found[0] collects the largest numeric gap."""
    if isinstance(a, list) and len(a) == 1 and not isinstance(b, list) and not isinstance(b, dict):
        a = a[0]
    if isinstance(b, list) and len(b) == 1 and not isinstance(a, list) and not isinstance(a, dict):
        b = b[0]
    if isinstance(a, dict) or isinstance(b, dict):
        if not (isinstance(a, dict) and isinstance(b, dict)):
            return False
        if set(a) != set(b):
            return False
        return all(_compare(a[k], b[k], found) for k in a)
    if isinstance(a, list) or isinstance(b, list):
        if not (isinstance(a, list) and isinstance(b, list)) or len(a) != len(b):
            return False
        return all(_compare(x, y, found) for x, y in zip(a, b))
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if _is_number(a) and _is_number(b):
        gap = abs(float(a) - float(b))
        if math.isnan(gap):
            return False
        found[0] = max(found[0], gap)
        return gap <= TOLERANCE
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    return False


def compare_one(name):
    r_ms, r_value = read_output(OUTPUT_DIR / f"{name}-r.txt")
    py_ms, py_value = read_output(OUTPUT_DIR / f"{name}-python.txt")
    found = [0.0]
    matched = _compare(r_value, py_value, found)
    return {
        "name": name,
        "matched": matched,
        "max_abs_diff": found[0],
        "r_ms": r_ms,
        "python_ms": py_ms,
        "speedup": r_ms / py_ms if py_ms else math.inf,
    }


def main():
    rows = [compare_one(name) for name in FUNCTIONS]
    header = f"{'function':<14} {'matched':<8} {'max_abs_diff':>14} {'R ms':>12} {'Python ms':>12} {'speedup':>10}"
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{row['name']:<14} {('yes' if row['matched'] else 'no'):<8} "
            f"{row['max_abs_diff']:>14.3g} {row['r_ms']:>12.6f} "
            f"{row['python_ms']:>12.6f} {row['speedup']:>10.4f}"
        )
    text = "\n".join(lines) + "\n"
    (OUTPUT_DIR / "summary.txt").write_text(text, encoding="utf-8")
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
