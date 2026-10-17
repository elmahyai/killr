"""Compare the R and Python outputs of the core sim proofs.

Each output file holds one value per line, and the last line is the median time in milliseconds.
A proof matches when both files hold the same number of values and every value agrees within 1e-8.
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "output"
TOL = 1e-8
NAMES = [
    "sim-rng",
    "simE",
    "simV",
    "simEII",
    "simEEI",
    "simEEE",
    "simEEV",
    "simEVI",
    "simVEI",
    "sim-dispatch",
]


def read(path: Path) -> tuple[list[float], float]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    values = [float(v) for v in lines[:-1]]
    return values, float(lines[-1])


def compare(name: str) -> dict[str, object]:
    r_vals, r_ms = read(OUT / f"{name}-r.txt")
    p_vals, p_ms = read(OUT / f"{name}-python.txt")
    same_len = len(r_vals) == len(p_vals)
    diffs = [abs(a - b) for a, b in zip(r_vals, p_vals)] if same_len else [math.inf]
    max_diff = max(diffs) if diffs else 0.0
    matches = same_len and max_diff <= TOL and all(math.isfinite(d) for d in diffs)
    return {
        "name": name,
        "n_values": len(r_vals),
        "matches": "yes" if matches else "no",
        "max_abs_diff": max_diff,
        "r_ms": r_ms,
        "python_ms": p_ms,
        "speedup": r_ms / p_ms if p_ms > 0 else math.inf,
    }


def main() -> None:
    rows = [compare(name) for name in NAMES]
    header = f"{'proof':<14}{'values':>8}  {'matches':<8}{'max_abs_diff':>16}{'R_ms':>12}{'Py_ms':>12}{'speedup':>10}"
    lines = [header]
    for row in rows:
        lines.append(
            f"{row['name']:<14}{row['n_values']:>8}  {row['matches']:<8}"
            f"{row['max_abs_diff']:>16.3e}{row['r_ms']:>12.4f}{row['python_ms']:>12.4f}{row['speedup']:>10.4f}"
        )
    text = "\n".join(lines) + "\n"
    (OUT / "sim-core-compare.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
