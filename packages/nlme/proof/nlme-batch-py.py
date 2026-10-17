import csv
import math
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
from nlme.nlslist import nlsList  # noqa: E402

DATA_CSV = Path(__file__).resolve().parent / "data" / "nlme-loblolly.csv"

# levels(Loblolly$Seed) in R: the group order nlme uses, not the sorted order.
LOBLOLLY_LEVELS = ("329", "327", "325", "307", "331", "311", "315", "321", "319", "301",
                   "323", "309", "303", "305")


class Frame:
    def __init__(self, columns, group_levels=None):
        self.columns = columns
        if group_levels is not None:
            self.group_levels = group_levels


def height_data():
    age = [2, 4, 6, 8, 10] * 4
    group = [name for name in "ABCD" for _ in range(5)]
    shift = [value for value in (-4, 1, 3, -2) for _ in range(5)]
    noise = [
        0.2, -0.1, 0.4, -0.3, 0.1, 0.0, 0.3, -0.2, 0.1, -0.4,
        -0.2, 0.2, 0.0, -0.1, 0.3, 0.1, -0.3, 0.2, 0.0, -0.2,
    ]
    height = [
        (100 + bi) + (15 - (100 + bi)) * math.exp(-math.exp(-3.2) * a) + e
        for a, bi, e in zip(age, shift, noise)
    ]
    return Frame(columns={"height": height, "age": age, "group": group})


def loblolly():
    with DATA_CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns = {
        "Seed": [row["Seed"] for row in rows],
        "age": [float(row["age"]) for row in rows],
        "height": [float(row["height"]) for row in rows],
    }
    return Frame(columns, LOBLOLLY_LEVELS)


HEIGHT = height_data()
FRAME = loblolly()


def sorted_by_name(matrix):
    """Rows in name order, as R's ranef(fl)[order(rownames)]; the rows follow the group levels."""
    perm = [LOBLOLLY_LEVELS.index(name) for name in sorted(LOBLOLLY_LEVELS)]
    return np.asarray(matrix, dtype=np.float64)[perm]


def one():
    fm = nlme(
        "height ~ SSasymp(age, Asym, R0, lrc)",
        HEIGHT,
        fixed="Asym + R0 + lrc ~ 1",
        random="Asym ~ 1",
        groups="~ group",
        start={"Asym": 100.0, "R0": 15.0, "lrc": -3.2},
    )
    fit = nlsList(
        "height ~ SSasympOff(age, Asym, lrc, c0) | Seed",
        FRAME,
        start={"Asym": 100.0, "lrc": -1.5, "c0": 0.0},
    )
    fl = nlme(fit, random="Asym ~ 1")
    fit0 = nlsList("height ~ SSasympOff(age, Asym, lrc, c0) | Seed", FRAME)
    fl0 = nlme(fit0, random="Asym ~ 1")
    fp = nlme(
        "height ~ SSasymp(age, Asym, R0, lrc)",
        FRAME,
        fixed="Asym + R0 + lrc ~ 1",
        random="pdDiag(Asym + R0 ~ 1)",
        groups="~ Seed",
        start={"Asym": 103.0, "R0": -8.5, "lrc": -3.3},
    )
    cov = fp.covariances["Seed"]
    return np.concatenate(
        [
            np.asarray(fm.fixed, dtype=np.float64),
            np.asarray([fm.sigma, fm.loglik], dtype=np.float64),
            np.ravel(next(iter(fm.random.values())), order="F"),
            np.asarray(fl.fixed, dtype=np.float64),
            np.asarray([fl.sigma, fl.loglik], dtype=np.float64),
            np.ravel(sorted_by_name(next(iter(fl.random.values()))), order="F"),
            np.asarray(fl0.fixed, dtype=np.float64),
            np.asarray([fl0.sigma, fl0.loglik], dtype=np.float64),
            np.asarray(fp.fixed, dtype=np.float64),
            np.asarray([cov[0, 0], cov[0, 1], cov[1, 1], fp.sigma, fp.loglik], dtype=np.float64),
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
