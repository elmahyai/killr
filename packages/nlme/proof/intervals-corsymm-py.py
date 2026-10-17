import json
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nlme.conlin import ConLin
from nlme.corsymm import corSymm
from nlme.gls import GlsObject
from nlme.glsapvar import glsApVar
from nlme.glsstruct import GlsStruct
from nlme.initialize import Initialize
from nlme.intervals import intervals

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "gls-orthodont.csv"
FIXTURE = HERE / "data" / "gls-orthodont-corSymm.json"


def load_frame():
    """Orthodont rows sorted by Subject then age, as the R proof sorts them."""
    frame = pd.read_csv(DATA)
    return frame.sort_values(["Subject", "age"], kind="stable").reset_index(drop=True)


def load_fit():
    """The gls fit with corSymm(form = ~ 1 | Subject), as R fitted it (fixed input).

    The translated gls cannot fit a corSymm correlation yet, so the fitted values
    come from the R fit in the fixture. The corSymm object, the ConLin, and the
    apVar matrix are built here from those values in the untimed setup.
    """
    fx = json.loads(FIXTURE.read_text())
    frame = load_frame()
    n = len(frame)
    female = (frame["Sex"].to_numpy() == "Female").astype(np.float64)
    x = np.column_stack([np.ones(n), frame["age"].to_numpy(np.float64), female])
    y = frame["distance"].to_numpy(np.float64)
    con = ConLin(
        Xy=np.column_stack([x, y]),
        dims={"N": n, "p": 3, "REML": int(fx["REML"])},
        logLik=0.0,
        sigma=0.0,
        fixedSigma=False,
        names=("(Intercept)", "age", "SexFemale", "distance"),
    )
    cs = Initialize(corSymm(form="~ 1 | Subject"), {"Subject": frame["Subject"].to_numpy(object)})
    cs = replace(cs, value=np.asarray(fx["corSymm_unconstrained"], dtype=np.float64))
    gls_st = GlsStruct(components={"corStruct": cs}, fixedSigma=False)
    sigma = float(fx["sigma"])
    k = len(fx["coefficients"])
    # The apVar matrix is the translated glsApVar, computed in the untimed setup.
    apvar = glsApVar(gls_st, sigma, con, natural=True)
    return GlsObject(
        modelStruct=gls_st,
        dims={"N": n, "p": 3, "REML": int(fx["REML"])},
        coefficients=np.asarray(fx["coefficients"], dtype=np.float64),
        coef_names=tuple(fx["coef_names"]),
        varBeta=np.asarray(fx["varBeta"], dtype=np.float64).reshape((k, k), order="F"),
        sigma=sigma,
        apVar=apvar,
        logLik=float(fx["logLik"]),
        numIter=0,
        fitted=np.zeros(0, dtype=np.float64),
        residuals=np.zeros(0, dtype=np.float64),
        method="REML",
        fixedSigma=False,
    )


def one(obj):
    res = intervals(obj, level=0.95, which="all")
    return np.concatenate(
        [
            np.asarray(res.coef, dtype=np.float64).reshape(-1, order="F"),
            np.asarray(res.structures["corStruct"], dtype=np.float64).reshape(-1, order="F"),
            np.asarray(res.sigma, dtype=np.float64).reshape(-1),
        ]
    )


obj = load_fit()
value = one(obj)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(obj)
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(v) for v in value), statistics.median(elapsed))
)
