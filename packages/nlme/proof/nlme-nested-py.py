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

DATA_CSV = Path(__file__).resolve().parent / "data" / "nlme-pixel.csv"


class Frame:
    def __init__(self, columns, group_levels=None):
        self.columns = columns
        if group_levels is not None:
            self.group_levels = group_levels


def pixel():
    with DATA_CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns = {
        "Dog": [row["Dog"] for row in rows],
        "Side": [row["Side"] for row in rows],
        "day": [float(row["day"]) for row in rows],
        "pixel": [float(row["pixel"]) for row in rows],
    }
    return Frame(columns)


DATA = pixel()


def one():
    fit = nlme(
        "pixel ~ SSasymp(day, Asym, R0, lrc)",
        DATA,
        fixed="Asym + R0 + lrc ~ 1",
        random={"Dog": "Asym ~ 1", "Side": "Asym ~ 1"},
        groups="~ Dog/Side",
        start={"Asym": 1090.0, "R0": 1040.0, "lrc": -2.0},
    )
    return np.concatenate(
        [
            np.asarray(fit.fixed, dtype=np.float64),
            np.array([fit.covariances["Dog"][0, 0], fit.covariances["Side"][0, 0], fit.sigma], dtype=np.float64),
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
