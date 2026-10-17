"""Run the R and Python nlme random-structure proofs and compare them.

Usage: python compare-nlme-random.py [random-slope nested pddiag]

Each proof prints one JSON line: ``value`` (the compared numbers) and
``median_ms`` (the median of 20 timed calls after one untimed call). The
checks are ``max_abs_diff <= 1e-8`` and ``speedup = R time / Python time``.
Outputs go to ``packages/nlme/docs/output``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
OUTPUT = PROOF.parent / "docs" / "output"
PYTHON = Path("/home/ahmed/killr_projects/killr/.venv/bin/python")
TOLERANCE = 1e-8

LABELS = {
    "random-slope": [
        "Asym", "R0", "lrc", "Var(Asym.(Intercept))", "Cov(Asym.(Intercept),Asym.age)",
        "Var(Asym.age)", "sigma", "logLik", "numIter",
    ],
    "nested": [
        "Asym", "R0", "lrc", "Var(Dog Asym)", "Var(Side Asym)", "sigma", "logLik", "numIter",
    ],
    "pddiag": [
        "Asym", "R0", "lrc", "Var(Asym)", "Cov(Asym,R0)", "Var(R0)", "sigma", "logLik", "numIter",
    ],
}


def last_json(text: str) -> dict:
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise RuntimeError("no JSON line in proof output")


def run_case(name: str) -> dict:
    r_run = subprocess.run(
        ["Rscript", str(PROOF / f"nlme-{name}-r.R")],
        capture_output=True, text=True, check=True,
    )
    py_run = subprocess.run(
        [str(PYTHON), str(PROOF / f"nlme-{name}-py.py")],
        capture_output=True, text=True, check=True,
    )
    r_json = last_json(r_run.stdout)
    py_json = last_json(py_run.stdout)
    r_values = r_json["value"]
    py_values = py_json["value"]
    if len(r_values) != len(py_values):
        raise RuntimeError(f"{name}: value lengths differ")
    diffs = [abs(a - b) for a, b in zip(r_values, py_values)]
    max_abs = max(diffs)
    worst = LABELS[name][diffs.index(max_abs)]
    speedup = r_json["median_ms"] / py_json["median_ms"]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / f"nlme-{name}-r.txt").write_text(r_run.stdout)
    (OUTPUT / f"nlme-{name}-python.txt").write_text(py_run.stdout)
    rows = [
        f"{label:34s} R={a:.12g}  Python={b:.12g}  abs diff={d:.3g}"
        for label, a, b, d in zip(LABELS[name], r_values, py_values, diffs)
    ]
    summary = [
        f"structure: {name}",
        f"matches: {'yes' if max_abs <= TOLERANCE else 'no'}",
        f"max_abs_diff: {max_abs:.3g} (at {worst})",
        f"R median_ms: {r_json['median_ms']:.4g}",
        f"Python median_ms: {py_json['median_ms']:.4g}",
        f"speedup: {speedup:.3g}",
        *rows,
    ]
    (OUTPUT / f"nlme-{name}-compare.txt").write_text("\n".join(summary) + "\n")
    return {
        "structure": name,
        "matches": max_abs <= TOLERANCE,
        "max_abs_diff": max_abs,
        "worst": worst,
        "speedup": speedup,
        "r_ms": r_json["median_ms"],
        "python_ms": py_json["median_ms"],
    }


def main(argv: list[str]) -> int:
    names = argv or ["random-slope", "nested", "pddiag"]
    for name in names:
        result = run_case(name)
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
