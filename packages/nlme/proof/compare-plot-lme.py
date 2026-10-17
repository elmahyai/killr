"""Compare the plot.lme proof against R and record the timing.

Runs the R proof (``Rscript``) and the Python proof with the same interpreter,
saves both stdout streams under ``docs/output``, and reports the largest
absolute difference between the plotted values: the x (fitted) and y (Pearson
residual) of the panel, and the reference line. The labelled points of the
``id = 0.05`` panel must have the same 1-based indexes and the same labels.
Matching means every plotted value is within 1e-8 and the labels are equal.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
PROOF = PACKAGE / "proof"
OUTPUT = PACKAGE / "docs" / "output"
TOLERANCE = 1e-8


def run(command: list[str]) -> str:
    done = subprocess.run(command, check=True, capture_output=True, text=True, cwd=PACKAGE)
    return done.stdout


def last_json_line(text: str) -> dict:
    lines = [line for line in text.splitlines() if line.startswith("{")]
    return json.loads(lines[-1])


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    r_text = run(["Rscript", str(PROOF / "plot.lme-r.R")])
    py_text = run([sys.executable, str(PROOF / "plot.lme-py.py")])
    (OUTPUT / "plot.lme-r.txt").write_text(r_text)
    (OUTPUT / "plot.lme-python.txt").write_text(py_text)
    r_value = last_json_line(r_text)
    py_value = last_json_line(py_text)

    r_vec = r_value["value"]
    py_vec = py_value["value"]
    if len(r_vec) != len(py_vec):
        raise SystemExit(f"length {len(py_vec)} differs from R {len(r_vec)}")
    n = (len(r_vec) - 2) // 2
    parts = {"x": (0, n), "y": (n, 2 * n), "abline": (2 * n, 2 * n + 2)}
    by_part = {
        part: max(abs(a - b) for a, b in zip(r_vec[start:stop], py_vec[start:stop]))
        for part, (start, stop) in parts.items()
    }
    max_diff = max(by_part.values())
    id_equal = r_value["value_id"] == py_value["value_id"]
    labels_equal = r_value["id_labels"] == py_value["id_labels"]
    labels_match = r_value["labels"] == py_value["labels"]
    r_ms = r_value["median_ms"]
    py_ms = py_value["median_ms"]
    summary = {
        "matches": bool(max_diff <= TOLERANCE and id_equal and labels_equal and labels_match),
        "max_abs_diff": max_diff,
        "max_abs_diff_by_quantity": by_part,
        "tolerance": TOLERANCE,
        "length": len(r_vec),
        "panels_r": r_value["panels"],
        "panels_python": py_value["panels"],
        "id_index_r": r_value["value_id"],
        "id_index_python": py_value["value_id"],
        "id_labels_r": r_value["id_labels"],
        "id_labels_python": py_value["id_labels"],
        "labels_r": r_value["labels"],
        "labels_python": py_value["labels"],
        "r_ms": r_ms,
        "python_ms": py_ms,
        "speedup": r_ms / py_ms,
    }
    (OUTPUT / "plot.lme-compare.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("matches", "max_abs_diff", "r_ms", "python_ms", "speedup")}))
    return 0 if summary["matches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
