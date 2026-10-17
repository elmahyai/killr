"""Run the R and Python proofs for me.weighted for every model and compare them.

Usage: .venv/bin/python proof/me.weighted-compare.py (from packages/mclust)

For each model, both sides make one untimed call, then 20 timed calls. The
reported time is the median in milliseconds. speedup = R time / Python time.
Each side prints loglik, bic, z, pro, mean, and sigma for unit weights (A) and
for non-unit weights (B). A model matches when every value agrees within 1e-8.
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
MODELS = [
    "E", "V",
    "EII", "VII", "EEI", "VEI", "EVI", "VVI",
    "EEE", "EEV", "VEV", "VEE", "EVE", "VVE", "EVV", "VVV",
]


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PKG))
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "exit %d" % proc.returncode)
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


def compare_model(model):
    r_text = run(["Rscript", str(HERE / "me.weighted-r.R"), model])
    py_text = run([sys.executable, str(HERE / "me.weighted-py.py"), model])
    r_labels, r_vals, r_ms = parse(r_text)
    py_labels, py_vals, py_ms = parse(py_text)
    if r_labels != py_labels:
        raise RuntimeError("label mismatch between R and Python")
    diffs = [abs(a - b) for a, b in zip(r_vals, py_vals)]
    finite = all(math.isfinite(v) for v in r_vals + py_vals)
    max_abs = max(diffs)
    worst = r_labels[diffs.index(max_abs)]
    stem = "me-weighted-%s" % model
    (OUT / (stem + "-r.txt")).write_text(
        "".join("%s %.17g\n" % (lab, val) for lab, val in zip(r_labels, r_vals))
        + "r_ms %.17g\n" % r_ms)
    (OUT / (stem + "-python.txt")).write_text(
        "".join("%s %.17g\n" % (lab, val) for lab, val in zip(py_labels, py_vals))
        + "translated_ms %.17g\n" % py_ms)
    return {
        "model": model,
        "values_compared": len(r_vals),
        "matches": bool(finite and max_abs <= TOL),
        "max_abs_diff": max_abs,
        "worst_value": worst,
        "tolerance": TOL,
        "r_ms": r_ms,
        "translated_ms": py_ms,
        "speedup": r_ms / py_ms,
        "r_output": "packages/mclust/docs/output/%s-r.txt" % stem,
        "python_output": "packages/mclust/docs/output/%s-python.txt" % stem,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for model in MODELS:
        try:
            row = compare_model(model)
        except RuntimeError as exc:
            row = {"model": model, "matches": False, "error": str(exc)}
        rows.append(row)
        print(json.dumps(row))
    (OUT / "me-weighted-compare.txt").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
