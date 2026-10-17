"""Compare the R and Python outputs of the `em` proof, and write the summary.

Reads docs/output/em-r.txt and docs/output/em-python.txt. Keys must match
exactly, values are compared with max absolute difference, and NaN matches
only NaN. `matches` is yes only when the keys match, there are values to
compare, and the max difference is within 1e-8.
"""

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs" / "output"
TOL = 1e-8


def read(path):
    keys, values, timing = [], {}, None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        name, _, rest = line.partition("\t")
        if name == "TIMING_MEDIAN_MS":
            timing = float(rest)
            continue
        keys.append(name)
        values[name] = [math.nan if t == "nan" else float(t) for t in rest.split()]
    return keys, values, timing


def main():
    r_keys, r_vals, r_ms = read(ROOT / "em-r.txt")
    p_keys, p_vals, p_ms = read(ROOT / "em-python.txt")

    keys_equal = r_keys == p_keys
    max_diff = 0.0
    n_values = 0
    worst = None
    for k in r_keys:
        a = r_vals.get(k, [])
        b = p_vals.get(k, [])
        if len(a) != len(b):
            max_diff = math.inf
            worst = (k, "length")
            continue
        for x, y in zip(a, b):
            n_values += 1
            if math.isnan(x) and math.isnan(y):
                d = 0.0
            elif math.isnan(x) or math.isnan(y):
                d = math.inf
            else:
                d = abs(x - y)
            if d > max_diff:
                max_diff = d
                worst = (k, x, y)
    for k in p_keys:
        if k not in r_vals:
            keys_equal = False

    matches = keys_equal and n_values > 0 and max_diff <= TOL
    speedup = r_ms / p_ms
    lines = [
        f"matches: {'yes' if matches else 'no'}",
        f"keys_equal: {keys_equal}",
        f"comparisons: {len(r_keys)} fields, {n_values} values",
        f"max_abs_diff: {max_diff:.3g}",
        f"worst: {worst}",
        f"r_median_ms: {r_ms:.6g}",
        f"python_median_ms: {p_ms:.6g}",
        f"speedup_r_over_python: {speedup:.4g}",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / "em-compare.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
