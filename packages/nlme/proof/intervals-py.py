import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nlme.gls import gls
from nlme.intervals import intervals

DATA = Path(__file__).resolve().parent / "data" / "gls-orthodont.csv"


def load():
    frame = pd.read_csv(DATA)
    frame["Sex"] = pd.Categorical(frame["Sex"], categories=["Male", "Female"])
    return frame


def one(fit_free, fit_fixed):
    a = intervals(fit_free, level=0.95, which="all")
    b = intervals(fit_fixed, level=0.95, which="all")
    return np.concatenate(
        [
            np.asarray(a.coef, dtype=np.float64).reshape(-1, order="F"),
            np.asarray(a.sigma, dtype=np.float64).reshape(-1),
            np.asarray(b.coef, dtype=np.float64).reshape(-1, order="F"),
            np.asarray(b.sigma, dtype=np.float64).reshape(-1),
        ]
    )


frame = load()
# The fits are untimed setup, as in the R proof; only intervals() is timed.
fit_free = gls("distance ~ age + Sex", frame)
fit_fixed = gls("distance ~ age + Sex", frame, control={"sigma": 2})
value = one(fit_free, fit_fixed)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(fit_free, fit_fixed)
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(v) for v in value), statistics.median(elapsed))
)
