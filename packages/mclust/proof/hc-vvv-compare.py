"""Compare hc-vvv-r.R and hc-vvv-py.py outputs, per case.

Run from packages/mclust:
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/hc-vvv-compare.py

Reads docs/output/hc-vvv-r.txt and docs/output/hc-vvv-python.txt and writes
docs/output/hc-vvv-compare.txt. A case matches when the dimensions, the hc merge
matrix, the hclust merge, height and order agree within 1e-8 (the merge matrix and
order exactly as integers in value).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
OUT = PKG / "docs" / "output"
TOL = 1e-8
KEYS = ["dim", "hc", "merge", "height", "order"]


def load(path):
    records = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        head, _, value = line.partition("\t")
        case, _, key = head.partition("|")
        records[(case, key)] = value
    return records


def nums(text):
    return np.array([float(v) for v in text.split()], dtype=float)


r = load(OUT / "hc-vvv-r.txt")
py = load(OUT / "hc-vvv-python.txt")
cases = []
for case, key in r:
    if case not in cases:
        cases.append(case)

rows = []
header = ("case", "path", "what", "matches", "max_abs_diff", "first_merge_differs",
          "r_ms", "translated_ms", "speedup")
for case in cases:
    path = "hcVVV" if case.startswith("hcVVV") else "hc"
    what = r[(case, "what")]
    problems = []
    max_diff = 0.0
    for key in KEYS:
        a = r.get((case, key))
        b = py.get((case, key))
        if a is None or b is None:
            problems.append(f"missing {key}")
            continue
        va, vb = nums(a), nums(b)
        if va.shape != vb.shape:
            problems.append(f"{key} shape")
            continue
        if va.size:
            diff = float(np.max(np.abs(va - vb)))
            max_diff = max(max_diff, diff)
            if diff > TOL:
                problems.append(f"{key} differs by {diff:.3g}")
    if py.get((case, "what")) != what:
        problems.append("what differs")

    # The first merge (1-based column of the hc matrix) where R and Python differ.
    first = "none"
    dims = nums(r[(case, "dim")]).astype(int)
    if (case, "hc") in r and (case, "hc") in py:
        ra = nums(r[(case, "hc")]).reshape(dims, order="F")
        pb = nums(py[(case, "hc")]).reshape(dims, order="F")
        cols = np.flatnonzero(np.any(ra != pb, axis=0))
        if cols.size:
            first = str(int(cols[0]) + 1)

    r_ms = float(r[(case, "time_ms")])
    py_ms = float(py[(case, "time_ms")])
    matches = not problems
    rows.append({
        "case": case,
        "path": path,
        "what": what,
        "matches": "yes" if matches else "no",
        "max_abs_diff": max_diff,
        "first_merge_differs": first,
        "r_ms": r_ms,
        "translated_ms": py_ms,
        "speedup": r_ms / py_ms,
        "problems": "; ".join(problems),
    })

lines = ["\t".join(header)]
for row in rows:
    lines.append("\t".join([
        row["case"], row["path"], row["what"], row["matches"],
        "%.3g" % row["max_abs_diff"], row["first_merge_differs"],
        "%.6g" % row["r_ms"], "%.6g" % row["translated_ms"], "%.4g" % row["speedup"],
    ]) + ("\t" + row["problems"] if row["problems"] else ""))
text = "\n".join(lines) + "\n"
(OUT / "hc-vvv-compare.txt").write_text(text)
print(text)
