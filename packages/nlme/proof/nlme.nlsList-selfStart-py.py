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
from nlme.nlme_generic import nlme
from nlme.nlslist import nlsList

LOBLOLLY_CSV = Path(__file__).resolve().parent / "data" / "nlme-loblolly.csv"


class Frame:
    """Columns of the Loblolly data with the factor levels in sorted order."""

    def __init__(self, columns, group_levels):
        self.columns = columns
        self.group_levels = group_levels


def loblolly():
    import csv

    with LOBLOLLY_CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns = {
        "Seed": [row["Seed"] for row in rows],
        "age": [float(row["age"]) for row in rows],
        "height": [float(row["height"]) for row in rows],
    }
    return Frame(columns, tuple(sorted(set(columns["Seed"]))))


FRAME = loblolly()


def one():
    fit = nlsList("height ~ SSasympOff(age, Asym, lrc, c0) | Seed", FRAME)
    fm = nlme(fit, random="Asym ~ 1")
    ranef = np.ravel(next(iter(fm.random.values())), order="F")
    return np.concatenate(
        [
            np.asarray(fm.fixed, dtype=np.float64),
            np.asarray([fm.sigma, fm.loglik], dtype=np.float64),
            ranef,
        ]
    )

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
