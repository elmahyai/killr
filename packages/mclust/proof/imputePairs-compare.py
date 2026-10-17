"""Compare the R and Python imputePairs records token by token.

Numbers must agree within 1e-8. Words such as usr, pch, col, labels and panel
tags must match exactly. The MS line is the median time in milliseconds.
"""

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "output"
TOLERANCE = 1e-8


def load(path):
    lines = [line.rstrip("\n") for line in open(path, encoding="utf-8")]
    ms = [float(line.split()[1]) for line in lines if line.startswith("MS ")]
    body = [line for line in lines if not line.startswith("MS ")]
    return body, ms[0]


def main():
    r_body, r_ms = load(OUT / "imputePairs-r.txt")
    p_body, p_ms = load(OUT / "imputePairs-py.txt")
    matches = len(r_body) == len(p_body)
    max_abs_diff = 0.0
    numbers = 0
    if not matches:
        print(f"line count differs: R {len(r_body)}, Python {len(p_body)}")
    for a, b in zip(r_body, p_body):
        ta, tb = a.split(), b.split()
        if len(ta) != len(tb):
            matches = False
            print(f"token count differs: {a[:60]!r}")
            continue
        for x, y in zip(ta, tb):
            try:
                fx, fy = float(x), float(y)
            except ValueError:
                if x != y:
                    matches = False
                    print(f"word differs: {x!r} vs {y!r}")
                continue
            numbers += 1
            max_abs_diff = max(max_abs_diff, abs(fx - fy))
    matches = matches and max_abs_diff <= TOLERANCE
    print(f"lines {len(r_body)}")
    print(f"numbers compared {numbers}")
    print(f"max_abs_diff {max_abs_diff:.3g}")
    print(f"tolerance {TOLERANCE:g}")
    print(f"matches {str(matches).lower()}")
    print(f"r_ms {r_ms:.6g}")
    print(f"translated_ms {p_ms:.6g}")
    print(f"speedup {r_ms / p_ms:.6g}")


if __name__ == "__main__":
    main()
