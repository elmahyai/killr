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
# The R fit of distance ~ age + Sex on the same CSV rows (Subject levels alphabetical).
BASE = json.loads((HERE / "data" / "gls-orthodont-corSymm.json").read_text())
# The R fit of distance ~ age on the same CSV rows, written with %.17g.
SECOND = {
    "p": 2, "sigma": 2.5279710124560681,
    "coefficients": [16.606398076769171, 0.67475573169060465],
    "coef_names": ["(Intercept)", "age"],
    "varBeta": [0.70093472538579826, -0.049007517231871391,
                -0.049007517231871391, 0.0045991575215044858],
    "corSymm_unconstrained": [-0.9798610493970592, -1.0639952198028697,
                              -0.37475540132932678, -0.85513936160881965,
                              -0.84119943645205353, -0.82720043277746014],
    "logLik": -219.66824357912324,
}


def make_fit(fx, with_sex):
    """GlsObject for a natural = FALSE gls fit. The apVar is the translated glsApVar."""
    d = pd.read_csv(DATA).sort_values(["Subject", "age"], kind="stable")
    x = np.column_stack([np.ones(len(d)), d.age] +
                         ([d.Sex.eq("Female")] if with_sex else []))
    y = d.distance.to_numpy()
    p = fx["p"]
    con = ConLin(Xy=np.column_stack([x, y]),
                 dims={"N": len(d), "p": p, "REML": 1}, logLik=0.0, sigma=0.0,
                 fixedSigma=False, names=tuple(fx["coef_names"]) + ("distance",))
    cs = Initialize(corSymm(form="~ 1 | Subject"),
                    {"Subject": d.Subject.to_numpy(object)})
    cs = replace(cs, value=np.asarray(fx["corSymm_unconstrained"], dtype=float))
    st = GlsStruct(components={"corStruct": cs}, fixedSigma=False)
    av = glsApVar(st, fx["sigma"], con, natural=False)
    return GlsObject(modelStruct=st, dims={"N": len(d), "p": p, "REML": 1},
                     coefficients=np.asarray(fx["coefficients"]), coef_names=tuple(fx["coef_names"]),
                     varBeta=np.asarray(fx["varBeta"]).reshape((p, p), order="F"),
                     sigma=fx["sigma"], apVar=av, logLik=fx["logLik"], numIter=0,
                     fitted=np.zeros(0), residuals=np.zeros(0), method="REML",
                     fixedSigma=False)


def one(obj):
    a = intervals(obj, level=0.95, which="all")
    return np.concatenate([a.coef.reshape(-1, order="F"),
                           a.structures["corStruct"].reshape(-1, order="F"),
                           a.sigma])


# The fixed inputs are built in the untimed setup; only intervals() is timed.
objs = [make_fit(BASE, True), make_fit(SECOND, False)]
for name, obj in zip(("Orthodont_age_Sex", "Orthodont_age"), objs):
    value = one(obj)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one(obj)
        elapsed.append((time.perf_counter() - started) * 1000)
    print("%s %s" % (name, json.dumps(
        {"value": [float(v) for v in value],
         "median_ms": statistics.median(elapsed)})))
