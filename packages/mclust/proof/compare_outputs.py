"""Compare R and Python proof output for one function.

Usage: python compare_outputs.py <name>
Reads docs/output/<name>-r.txt and docs/output/<name>-python.txt. Each file
holds one value per line, then the median time in ms on the last line.
Writes docs/output/<name>-compare.txt.

Layout per case, for a p-column input: returnCode, loglik, mean (p),
Sigma (p*p, column-major), cholSigma (p*p, column-major). Cases are A (p=4),
B (p=3), C (p=2).
"""

import sys
from pathlib import Path

import numpy as np

TOL = 1e-8
root = Path(__file__).resolve().parents[1]
out_dir = root / "docs" / "output"
name = sys.argv[1]

r_lines = (out_dir / f"{name}-r.txt").read_text().split()
p_lines = (out_dir / f"{name}-python.txt").read_text().split()
r_ms = float(r_lines[-1])
py_ms = float(p_lines[-1])
r_vals = np.array([float(v) for v in r_lines[:-1]])
p_vals = np.array([float(v) for v in p_lines[:-1]])

same_shape = r_vals.shape == p_vals.shape
max_abs = float(np.max(np.abs(r_vals - p_vals))) if same_shape and r_vals.size else float("inf")
matches = bool(same_shape and max_abs <= TOL)

# Diagnostic only: the cholSigma sign bug. Negating the Python cholSigma gives
# the difference that the bug would have shown.
flip_max = float("nan")
if same_shape:
    flip_diffs = []
    pos = 0
    for p in (4, 3, 2):
        size = 2 + p + 2 * p * p
        r_chol = r_vals[pos + size - p * p: pos + size]
        p_chol = p_vals[pos + size - p * p: pos + size]
        flip_diffs.append(np.max(np.abs(r_chol - (-p_chol))))
        pos += size
    flip_max = float(max(flip_diffs))

speedup = r_ms / py_ms
lines = [
    f"{name}: matches={'yes' if matches else 'no'} (tol {TOL})",
    f"values R={r_vals.size} Python={p_vals.size}",
    f"max_abs_diff={max_abs:.3e}",
    f"R_ms={r_ms:.6f}",
    f"Python_ms={py_ms:.6f}",
    f"speedup={speedup:.3f}",
    f"diagnostic: max diff if cholSigma sign were flipped={flip_max:.3e}",
]
text = "\n".join(lines) + "\n"
(out_dir / f"{name}-compare.txt").write_text(text)
print(text, end="")
