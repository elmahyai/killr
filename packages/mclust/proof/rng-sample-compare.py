"""Compare the R and Python sample.int and runif records line by line.

A line matches when its label is the same and its numbers agree within 1e-8.
The report names every line that does not match.
"""

import re
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "output"
TOLERANCE = 1e-8
NUMBER = re.compile(r"-?[0-9.]+(?:e[-+]?[0-9]+)?")


def split(line):
    tokens = line.split()
    words = [t for t in tokens if not NUMBER.fullmatch(t)]
    values = [float(t) for t in tokens if NUMBER.fullmatch(t)]
    return words, values


def main():
    r_lines = [line for line in open(OUT / "rng-sample-r.txt", encoding="utf-8") if line.strip()]
    p_lines = [line for line in open(OUT / "rng-sample-py.txt", encoding="utf-8") if line.strip()]
    print(f"lines {len(r_lines)} R, {len(p_lines)} Python")
    max_abs_diff = 0.0
    mismatched = []
    for a, b in zip(r_lines, p_lines):
        wa, va = split(a)
        wb, vb = split(b)
        if wa != wb or len(va) != len(vb):
            mismatched.append(" ".join(wa)[:60] + " (shape)")
            continue
        diff = max([abs(x - y) for x, y in zip(va, vb)] or [0.0])
        max_abs_diff = max(max_abs_diff, diff)
        if diff > TOLERANCE:
            mismatched.append(" ".join(wa)[:60] + f" (diff {diff:.3g})")
    print(f"max_abs_diff {max_abs_diff:.3g}")
    print(f"tolerance {TOLERANCE:g}")
    print(f"matched {len(r_lines) - len(mismatched)} of {len(r_lines)}")
    for item in mismatched:
        print(f"mismatch {item}")


if __name__ == "__main__":
    main()
