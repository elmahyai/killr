"""Compare the R and Python outputs of the five EM proofs.

Reads docs/output/<name>-r.txt and docs/output/<name>-python.txt, where each file
holds the values (one per line) and the median time in ms as its last line.
Writes docs/output/<name>-compare.txt and prints one summary line per function.
"""
import math
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "output"
TOL = 1e-8


def read(path: Path):
    lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    values = [float("nan") if ln == "NA" else float(ln) for ln in lines[:-1]]
    return values, float(lines[-1])


def compare(name: str) -> str:
    r_vals, r_ms = read(OUT / f"{name}-r.txt")
    p_vals, p_ms = read(OUT / f"{name}-python.txt")
    if len(r_vals) != len(p_vals):
        matches, max_diff = False, float("inf")
    else:
        max_diff = 0.0
        matches = True
        for a, b in zip(r_vals, p_vals):
            if math.isnan(a) or math.isnan(b):
                if math.isnan(a) != math.isnan(b):
                    matches, max_diff = False, float("inf")
                    break
                continue
            d = abs(a - b)
            max_diff = max(max_diff, d)
            if d > TOL:
                matches = False
    speedup = r_ms / p_ms if p_ms > 0 else float("inf")
    yesno = "yes" if matches else "no"
    line = (f"{name}: matches={yesno} n_values={len(r_vals)}/{len(p_vals)} "
            f"max_abs_diff={max_diff:.3g} R_ms={r_ms:.4g} Python_ms={p_ms:.4g} speedup={speedup:.4g}")
    (OUT / f"{name}-compare.txt").write_text(line + "\n")
    return line


if __name__ == "__main__":
    for name in sys.argv[1:] or ["emE", "emEEI", "emEII", "emEVI", "emV"]:
        print(compare(name))
