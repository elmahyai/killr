"""Compare an R proof record file with its Python twin (mclust gap proofs).

Usage (from packages/mclust):
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/mclust_gaps_compare.py NAME

reads docs/output/NAME-r.txt and docs/output/NAME-py.txt, matches records by key
(the first tab-separated field group), and prints one line per key with the
largest absolute difference. Writes docs/output/NAME-compare.txt and prints
the overall max_abs_diff, the number of records, and the status.
Missing and NA values must agree in position. Strings must agree exactly.
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TOL = 1e-8


def load(path):
    records = {}
    order = []
    for line in path.read_text().splitlines():
        parts = line.split("\t")
        if not parts or parts[0] == "":
            continue
        key = parts[0]
        if key == "time_ms":
            records[key] = parts[1:]
            continue
        # The key is the last field name before the values; values are numeric
        # or NA/NULL, or a string (modelName). Records are distinct by their key.
        name, values = _split(parts)
        if name in records:
            raise ValueError(f"duplicate key {name} in {path.name}")
        records[name] = values
        order.append(name)
    return records, order


def _split(parts):
    # R and Python write "PREFIX\tFIELD\tv1\tv2..." (or "FIELD\tv..."). A field
    # name is never a number, a NA, or NULL, so the first token that parses as a
    # value marks where the values start. modelName is the one string value.
    if len(parts) >= 3 and parts[1] == "modelName":
        return "\t".join(parts[:2]), parts[2:]
    name = []
    for i, token in enumerate(parts):
        if i > 0 and _is_value(token):
            return "\t".join(name), parts[i:]
        name.append(token)
    return "\t".join(name), []


def _is_value(token):
    if token in ("NA", "NULL"):
        return True
    try:
        float(token)
        return True
    except ValueError:
        return False


def compare(r_values, p_values):
    if r_values == ["NULL"] or p_values == ["NULL"]:
        return ("NULL-match" if r_values == p_values else "NULL-mismatch"), 0.0
    if len(r_values) != len(p_values):
        return "length-mismatch", float("inf")
    if any(not _is_value(v) for v in r_values) or any(not _is_value(v) for v in p_values):
        return ("string-match" if r_values == p_values else "string-mismatch"), 0.0
    a = np.array([np.nan if v == "NA" else float(v) for v in r_values])
    b = np.array([np.nan if v == "NA" else float(v) for v in p_values])
    if not np.array_equal(np.isnan(a), np.isnan(b)):
        return "NA-mismatch", float("inf")
    mask = ~np.isnan(a)
    if not mask.any():
        return "ok", 0.0
    diff = float(np.max(np.abs(a[mask] - b[mask])))
    return "ok", diff


def main(name):
    out = ROOT / "docs" / "output"
    r_records, r_order = load(out / f"{name}-r.txt")
    p_records, _ = load(out / f"{name}-py.txt")
    lines = []
    worst = 0.0
    failures = []
    for key in r_order:
        if key not in p_records:
            failures.append(f"{key}: missing in python")
            lines.append(f"{key}\tMISSING")
            continue
        status, diff = compare(r_records[key], p_records[key])
        worst = max(worst, diff)
        if status != "ok" and not status.endswith("match"):
            failures.append(f"{key}: {status}")
        if diff > TOL:
            failures.append(f"{key}: max_abs_diff {diff:.3g} above tolerance")
        lines.append(f"{key}\t{status}\t{diff:.3g}")
    timing = {}
    for label, path in (("r", out / f"{name}-r.txt"), ("py", out / f"{name}-py.txt")):
        values = load(path)[0].get("time_ms")
        timing[label] = float(values[0]) if values else float("nan")
    speedup = timing["r"] / timing["py"] if timing["py"] else float("nan")
    matches = not failures
    summary = [
        f"matches\t{'yes' if matches else 'no'}",
        f"records\t{len(r_order)}",
        f"max_abs_diff\t{worst:.3g}",
        f"r_ms\t{timing['r']:.6g}",
        f"translated_ms\t{timing['py']:.6g}",
        f"speedup\t{speedup:.4g}",
    ]
    text = "\n".join(lines + summary + [f"failure\t{f}" for f in failures]) + "\n"
    (out / f"{name}-compare.txt").write_text(text)
    print(text, end="")
    return 0 if matches else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
