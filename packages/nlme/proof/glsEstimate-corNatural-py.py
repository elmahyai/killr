"""glsEstimate on the corNatural structure of Orthodont at R's gls optimum.

The structure is built as gls builds it (sorted by group, initialized), then set to
the R optimum in proof/data/gls-standin-optimum.json. glsEstimate runs no optimizer,
so no stand-in is involved here. Compare with proof/glsEstimate-corNatural-r.R.
"""

import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nlme.cornatural import corNatural
from nlme.gls import _structure_inputs
from nlme.glscontrol import glsControl
from nlme.glsapvar import coef_vector, set_coef
from nlme.glsestimate import glsEstimate

DATA = Path(__file__).resolve().parent / "data" / "gls-orthodont.csv"
OPTIMUM = Path(__file__).resolve().parent / "data" / "gls-standin-optimum.json"


def load():
    frame = pd.read_csv(DATA)
    # R's Orthodont Sex factor has levels Male, Female; the reference level is Male.
    frame["Sex"] = pd.Categorical(frame["Sex"], categories=["Male", "Female"])
    return frame


def build(frame):
    return _structure_inputs(
        "distance ~ age + Sex", frame, corNatural(form="~ 1 | Subject"), None, True, glsControl()
    )


frame = load()
inputs = build(frame)
optimum = np.asarray(json.loads(OPTIMUM.read_text())["corNatural"], dtype=np.float64)
assert optimum.size == coef_vector(inputs.gls_st).size, "fixture does not match the structure"
gls_st = set_coef(inputs.gls_st, optimum)
con_lin = inputs.con_lin


def one():
    fit = glsEstimate(gls_st, con_lin)
    return np.concatenate(
        [
            np.asarray(fit.beta, dtype=np.float64).reshape(-1),
            np.array([fit.sigma, fit.logLik], dtype=np.float64),
            np.asarray(fit.varBeta, dtype=np.float64).reshape(-1, order="F"),
            np.asarray(fit.fitted, dtype=np.float64).reshape(-1),
            np.asarray(fit.resid, dtype=np.float64).reshape(-1),
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
    % (",".join("%.17g" % float(v) for v in value), statistics.median(elapsed))
)
