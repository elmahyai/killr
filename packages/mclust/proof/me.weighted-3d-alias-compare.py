"""Compare me.weighted on 3-D models and the four R model aliases.

Usage: /home/ahmed/killr_projects/killr/.venv/bin/python \
    proof/me.weighted-3d-alias-compare.py
"""

import json
import math
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE.parent
OUT = PKG / "docs" / "output"
TOL = 1e-8
CASES = ["EEE", "VVV", "X", "XII", "XXI", "XXX"]


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PKG))
    if proc.returncode:
        detail = proc.stderr.strip().splitlines()
        raise RuntimeError(detail[-1] if detail else "exit %d" % proc.returncode)
    return proc.stdout


def parse(text):
    labels, values, timing = [], [], None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        if parts[0] in ("r_ms", "translated_ms"):
            timing = float(parts[1])
        else:
            labels.append(parts[0])
            values.append(float(parts[1]))
    return labels, values, timing


def compare_case(model):
    r_text = run(["Rscript", str(HERE / "me.weighted-3d-alias-r.R"), model])
    py_text = run([sys.executable, str(HERE / "me.weighted-3d-alias-py.py"), model])
    r_labels, r_vals, r_ms = parse(r_text)
    py_labels, py_vals, py_ms = parse(py_text)
    if r_labels != py_labels:
        raise RuntimeError("label mismatch between R and Python")
    diffs = [abs(a - b) for a, b in zip(r_vals, py_vals)]
    finite = all(math.isfinite(v) for v in r_vals + py_vals)
    max_abs = max(diffs)
    worst = r_labels[diffs.index(max_abs)]
    stem = "me-weighted-3d-%s" % model
    r_path = OUT / (stem + "-r.txt")
    py_path = OUT / (stem + "-python.txt")
    r_path.write_text(
        "".join("%s %.17g\n" % (lab, val) for lab, val in zip(r_labels, r_vals))
        + "r_ms %.17g\n" % r_ms
    )
    py_path.write_text(
        "".join("%s %.17g\n" % (lab, val) for lab, val in zip(py_labels, py_vals))
        + "translated_ms %.17g\n" % py_ms
    )
    return {
        "case": model,
        "matches": bool(finite and max_abs <= TOL),
        "max_abs_diff": max_abs,
        "worst_value": worst,
        "r_ms": r_ms,
        "translated_ms": py_ms,
        "speedup": r_ms / py_ms,
        "proof": [
            "packages/mclust/proof/me.weighted-3d-alias-r.R",
            "packages/mclust/proof/me.weighted-3d-alias-py.py",
        ],
        "r_output": "packages/mclust/docs/output/%s-r.txt" % stem,
        "translated_output": "packages/mclust/docs/output/%s-python.txt" % stem,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for model in CASES:
        try:
            row = compare_case(model)
        except RuntimeError as exc:
            row = {"case": model, "matches": False, "error": str(exc)}
        rows.append(row)
        print(json.dumps(row))
    (OUT / "me-weighted-3d-alias-compare.txt").write_text(
        json.dumps(rows, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
