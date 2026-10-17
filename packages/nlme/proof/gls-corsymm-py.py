"""gls with corSymm on two fixed datasets, with nlminb_port (PORT).

Orthodont: distance ~ age + Sex, corSymm(~ 1 | Subject); Loblolly: height ~ age,
corSymm(~ 1 | Seed). Each is fitted with control natural = FALSE and natural = TRUE.
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

from nlme.corsymm import coef as corsymm_coef
from nlme.corsymm import corSymm
from nlme.gls import gls

DATA = Path(__file__).resolve().parent / "data"


def load_orthodont():
    frame = pd.read_csv(DATA / "gls-orthodont.csv")
    # R's Orthodont Sex factor has levels Male, Female; the reference level is Male.
    frame["Sex"] = pd.Categorical(frame["Sex"], categories=["Male", "Female"])
    return frame


def load_loblolly():
    frame = pd.read_csv(DATA / "nlme-loblolly.csv", dtype={"Seed": str})
    return frame


def parts(fit):
    unc = np.asarray(corsymm_coef(fit.modelStruct.components["corStruct"], unconstrained=True).values, dtype=np.float64)
    var_beta = np.asarray(fit.varBeta, dtype=np.float64)
    # apVar is a message string when the Hessian is not negative definite (Loblolly,
    # natural = TRUE): the flag records which case, and the matrix is added only when it is one.
    is_msg = isinstance(fit.apVar, str)
    ap_matrix = np.zeros(0, dtype=np.float64) if is_msg else np.asarray(fit.apVar.values, dtype=np.float64).reshape(-1, order="F")
    return np.concatenate(
        [
            np.asarray(fit.coefficients, dtype=np.float64).reshape(-1),
            np.sqrt(np.diag(var_beta)),
            np.array([fit.sigma, fit.logLik], dtype=np.float64),
            unc,
            np.array([float(is_msg)], dtype=np.float64),
            ap_matrix,
        ]
    )


def one(orthodont, loblolly):
    return np.concatenate(
        [
            parts(gls("distance ~ age + Sex", orthodont, correlation=corSymm(form="~ 1 | Subject"), control={"natural": False})),
            parts(gls("distance ~ age + Sex", orthodont, correlation=corSymm(form="~ 1 | Subject"), control={"natural": True})),
            parts(gls("height ~ age", loblolly, correlation=corSymm(form="~ 1 | Seed"), control={"natural": False})),
            parts(gls("height ~ age", loblolly, correlation=corSymm(form="~ 1 | Seed"), control={"natural": True})),
        ]
    )


orthodont = load_orthodont()
loblolly = load_loblolly()
value = one(orthodont, loblolly)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(orthodont, loblolly)
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(v) for v in value), statistics.median(elapsed))
)
