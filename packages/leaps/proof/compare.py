"""Compare the R and Rust proof outputs and write ../docs/output/compare.txt.

Checks that the selected subsets match exactly and that the RSS values agree
within 1e-8. Timings are the medians recorded by each side.
"""

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "output"
TOL = 1e-8


def read_subsets(path: Path) -> dict:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        return {
            (int(r["predictors"]), int(r["rank"])): (float(r["rss"]), r["vars"])
            for r in reader
        }


def read_median(path: Path) -> float:
    for line in path.read_text().splitlines():
        if line.startswith("median_seconds:"):
            return float(line.split(":", 1)[1])
    raise ValueError(f"no median_seconds in {path}")


def main() -> int:
    r_sub = read_subsets(OUT / "r_subsets.csv")
    rust_sub = read_subsets(OUT / "rust_subsets.csv")

    problems = []
    if set(r_sub) != set(rust_sub):
        problems.append(
            f"subset keys differ: only R {sorted(set(r_sub) - set(rust_sub))}, "
            f"only Rust {sorted(set(rust_sub) - set(r_sub))}"
        )

    max_abs = 0.0
    vars_mismatch = 0
    for key in sorted(set(r_sub) & set(rust_sub)):
        r_rss, r_vars = r_sub[key]
        k_rss, k_vars = rust_sub[key]
        if r_vars != k_vars:
            vars_mismatch += 1
            problems.append(f"vars differ at {key}: R {r_vars} Rust {k_vars}")
        max_abs = max(max_abs, abs(r_rss - k_rss))

    if max_abs > TOL:
        problems.append(f"max abs RSS diff {max_abs:.3e} exceeds {TOL:.0e}")

    r_med = read_median(OUT / "r_timings.txt")
    rust_med = read_median(OUT / "rust_timings.txt")
    speedup = r_med / rust_med if rust_med > 0 else float("inf")

    status = "yes" if not problems else "no"
    r_ms = r_med * 1000.0
    python_ms = rust_med * 1000.0
    lines = [
        f"regsubsets: matches {status}, max abs diff {max_abs:.3e}, "
        f"R {r_ms:.3f} ms, Python {python_ms:.3f} ms, speedup {speedup:.2f}x",
        f"leaps: matches {status}, max abs diff {max_abs:.3e}, "
        f"R {r_ms:.3f} ms, Python {python_ms:.3f} ms, speedup {speedup:.2f}x",
    ]
    lines += [f"problem: {p}" for p in problems]
    text = "\n".join(lines) + "\n"
    (OUT / "compare.txt").write_text(text)
    print(text, end="")
    return 0 if status == "yes" else 1


if __name__ == "__main__":
    sys.exit(main())
