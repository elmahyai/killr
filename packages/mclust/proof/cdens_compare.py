"""Compare the R and Python outputs of the cdens proofs and write one comparison per function.

Each output file holds the values on lines before the last one, and the median
time in milliseconds on the last line. A function matches when the two value
vectors have the same length and the largest absolute difference is at most 1e-8.
"""

import sys
from pathlib import Path

import numpy as np

TOLERANCE = 1e-8
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"
FUNCTIONS = ["cdensV", "cdensVEI", "cdensVEV", "cdensVII", "cdensVVI", "cdensVVV", "cdensEVV"]


def read_output(path: Path) -> tuple[np.ndarray, float]:
    numbers = [float(token) for token in path.read_text().split()]
    return np.array(numbers[:-1], dtype=float), numbers[-1]


def main() -> int:
    failed = False
    for name in FUNCTIONS:
        r_vals, r_ms = read_output(OUTPUT / f"{name}-r.txt")
        py_vals, py_ms = read_output(OUTPUT / f"{name}-python.txt")
        if r_vals.shape != py_vals.shape:
            max_abs = float("inf")
            matches = False
        else:
            max_abs = float(np.max(np.abs(r_vals - py_vals)))
            matches = bool(max_abs <= TOLERANCE)
        speedup = r_ms / py_ms
        failed = failed or not matches
        line = (
            f"{name} matches={'yes' if matches else 'no'} "
            f"values={r_vals.size} max_abs_diff={max_abs:.3e} "
            f"r_ms={r_ms:.6g} python_ms={py_ms:.6g} speedup={speedup:.4g}"
        )
        print(line)
        (OUTPUT / f"{name}-compare.txt").write_text(line + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
