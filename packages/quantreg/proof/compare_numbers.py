"""Compare one R proof output with one Python proof output.

Usage: python compare_numbers.py <name>
Reads docs/output/<name>-r.txt and docs/output/<name>-python.txt. Each file ends with a
line of comma-separated values and a line with the median time in milliseconds.
Prints matches, max_abs_diff, r_ms, translated_ms, and speedup = R / Python.
Matches means every value agrees within 1e-8.
"""

import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "output"
TOLERANCE = 1e-8


def load(path):
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    values = [float(item) for item in lines[-2].replace(" ", "").rstrip(",").split(",") if item]
    return values, float(lines[-1])


def main(name):
    r_values, r_ms = load(OUT / f"{name}-r.txt")
    py_values, py_ms = load(OUT / f"{name}-python.txt")
    if len(r_values) != len(py_values):
        raise SystemExit(f"length R {len(r_values)} Python {len(py_values)}")
    worst = max(abs(a - b) for a, b in zip(r_values, py_values))
    print(f"matches {'yes' if worst <= TOLERANCE else 'no'}")
    print(f"n {len(r_values)}")
    print(f"max_abs_diff {worst:.17g}")
    print(f"r_ms {r_ms:.17g}")
    print(f"translated_ms {py_ms:.17g}")
    print(f"speedup {r_ms / py_ms:.17g}")


if __name__ == "__main__":
    main(sys.argv[1])
