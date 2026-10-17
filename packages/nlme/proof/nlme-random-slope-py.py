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

from nlme.nlme_generic import nlme  # noqa: E402

DATA_CSV = Path(__file__).resolve().parent / "data" / "nlme-loblolly.csv"

# levels(Loblolly$Seed) in R: the group order nlme uses, not the sorted order.
LOBLOLLY_LEVELS = ("329", "327", "325", "307", "331", "311", "315", "321", "319", "301",
                   "323", "309", "303", "305")


class Frame:
    def __init__(self, columns, group_levels=None):
        self.columns = columns
        if group_levels is not None:
            self.group_levels = group_levels


def loblolly():
    with DATA_CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns = {
        "Seed": [row["Seed"] for row in rows],
        "age": [float(row["age"]) for row in rows],
        "height": [float(row["height"]) for row in rows],
    }
    return Frame(columns, LOBLOLLY_LEVELS)


DATA = loblolly()


def one():
    fit = nlme(
        "height ~ SSasymp(age, Asym, R0, lrc)",
        DATA,
        fixed="Asym + R0 + lrc ~ 1",
        random="Asym ~ age",
        groups="~ Seed",
        start={"Asym": 103.0, "R0": -8.5, "lrc": -3.3},
    )
    cov = fit.covariances["Seed"]
    return np.concatenate(
        [
            np.asarray(fit.fixed, dtype=np.float64),
            np.array([cov[0, 0], cov[0, 1], cov[1, 1], fit.sigma], dtype=np.float64),
            np.array([fit.loglik, float(fit.num_iter)], dtype=np.float64),
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
