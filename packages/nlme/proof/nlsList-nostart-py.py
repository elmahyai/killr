"""nlsList no-start cases (SSasympOff initial values) against R, nlme 3.1-171.

Matches nlsList-nostart-r.R. Each case: one untimed call, then the median of 20 timed calls.
Values per group are the coefficients (Asym, lrc, c0), the residual standard error, and the
convergence flag, in the order of the nlsList groups.
"""

import csv
import json
import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Load the nlme modules without running nlme/__init__.py (it imports phenoModel).
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg
from nlme.nlslist import nlsList  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent / "data"
OUT_DIR = ROOT / "docs" / "output"


class GroupedFrame:
    """Column dict plus the group level order, as ``groupedData`` supplies it."""

    def __init__(self, columns, group_levels):
        self.columns = columns
        self.group_levels = group_levels


def load_frame(csv_name, levels_name, group, numeric):
    with open(DATA_DIR / csv_name, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    columns = {group: [row[group] for row in rows]}
    for name in numeric:
        columns[name] = [float(row[name]) for row in rows]
    levels = (DATA_DIR / levels_name).read_text(encoding="utf-8").split()
    return GroupedFrame(columns, tuple(levels))


LOBLOLLY = load_frame(
    "nlsList-nostart-loblolly.csv", "nlsList-nostart-loblolly-levels.txt", "Seed", ["age", "height"]
)
CO2 = load_frame("nlsList-nostart-co2.csv", "nlsList-nostart-co2-levels.txt", "Plant", ["conc", "uptake"])

CASES = [
    {
        "name": "loblolly-nostart",
        "formula": "height ~ SSasympOff(age, Asym, lrc, c0) | Seed",
        "frame": LOBLOLLY,
        "start": None,
    },
    {
        "name": "loblolly-start",
        "formula": "height ~ SSasympOff(age, Asym, lrc, c0) | Seed",
        "frame": LOBLOLLY,
        "start": {"Asym": 100.0, "lrc": -1.5, "c0": 0.0},
    },
    {
        "name": "co2-nostart",
        "formula": "uptake ~ SSasympOff(conc, Asym, lrc, c0) | Plant",
        "frame": CO2,
        "start": None,
    },
    {
        "name": "co2-start",
        "formula": "uptake ~ SSasympOff(conc, Asym, lrc, c0) | Plant",
        "frame": CO2,
        "start": {"Asym": 30.0, "lrc": -4.5, "c0": 52.0},
    },
]


def fit_case(case):
    return nlsList(case["formula"], case["frame"], start=case["start"])


def values_of(fit):
    out = []
    for name, entry in fit.entries:
        out.extend([entry.coefficients["Asym"], entry.coefficients["lrc"], entry.coefficients["c0"]])
        out.extend([entry.sigma, 1.0 if entry.converged else 0.0])
    return np.asarray(out, dtype=np.float64)


def example_lines(case, fit):
    lines = [f"case: {case['name']}", f"groups: {len(fit.entries)}"]
    for name, entry in fit.entries:
        c = entry.coefficients
        lines.append(
            f"{name}: {c['Asym']:.10g} {c['lrc']:.10g} {c['c0']:.10g} "
            f"sigma={entry.sigma:.10g} conv={entry.converged}"
        )
    return lines


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_lines = []
    results = []
    for case in CASES:
        fit = fit_case(case)
        all_lines.extend(example_lines(case, fit))
        all_lines.append("")
        value = values_of(fit)
        elapsed = []
        for _ in range(20):
            started = time.perf_counter()
            fit_case(case)
            elapsed.append((time.perf_counter() - started) * 1000)
        results.append(
            {
                "name": case["name"],
                "value": [float(part) for part in value],
                "median_ms": statistics.median(elapsed),
            }
        )
    (OUT_DIR / "nlsList-nostart-python.txt").write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    print(json.dumps({"cases": results}))


if __name__ == "__main__":
    main()
