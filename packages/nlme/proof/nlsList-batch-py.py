import csv
import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.nlslist import nlsList  # noqa: E402

DATA_CSV = Path(__file__).resolve().parent / "data" / "nlme-loblolly.csv"


class Frame:
    """Columns of the Loblolly data with the factor levels in sorted order."""

    def __init__(self, columns, group_levels):
        self.columns = columns
        self.group_levels = group_levels


def loblolly():
    with DATA_CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns = {
        "Seed": [row["Seed"] for row in rows],
        "age": [float(row["age"]) for row in rows],
        "height": [float(row["height"]) for row in rows],
    }
    return Frame(columns, tuple(sorted(set(columns["Seed"]))))


FRAME = loblolly()


def one():
    fit = nlsList(
        "height ~ SSasympOff(age, Asym, lrc, c0) | Seed",
        FRAME,
        start={"Asym": 100.0, "lrc": -1.5, "c0": 0.0},
    )
    rows = sorted((name, fit_obj) for name, fit_obj in fit.entries)
    cf = np.array(
        [[item.coefficients[p] for p in ("Asym", "lrc", "c0")] for _name, item in rows],
        dtype=np.float64,
    )
    return np.ravel(cf, order="F")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
