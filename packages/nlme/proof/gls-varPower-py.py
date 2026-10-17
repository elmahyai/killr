"""gls(distance ~ age + Sex, weights = varPower(~ age)) on Orthodont, with nlminb_port (PORT).

The outer loop is ``nlme.gls.gls`` with ``nlminb_port`` (crates/nlminb_port, PORT),
the same kernel R's nlminb runs. Compare with the matching ``-r.R`` file at 1e-8.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nlme.gls import gls
from nlme.var_power import varPower

DATA = Path(__file__).resolve().parent / "data" / "gls-orthodont.csv"


def load():
    frame = pd.read_csv(DATA)
    # R's Orthodont Sex factor has levels Male, Female; the reference level is Male.
    frame["Sex"] = pd.Categorical(frame["Sex"], categories=["Male", "Female"])
    return frame


def one(frame):
    fit = gls("distance ~ age + Sex", frame, weights=varPower(form="~ age"))
    var_beta = np.asarray(fit.varBeta, dtype=np.float64)
    return np.concatenate(
        [
            np.asarray(fit.coefficients, dtype=np.float64).reshape(-1),
            np.sqrt(np.diag(var_beta)),
            np.array([fit.sigma, fit.logLik], dtype=np.float64),
        ]
    )


frame = load()
value = one(frame)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(frame)
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(v) for v in value), statistics.median(elapsed))
)
