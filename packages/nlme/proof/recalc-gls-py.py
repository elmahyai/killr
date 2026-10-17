import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nlme.conlin import ConLin
from nlme.corar1 import CorAR1
from nlme.cornatural import CorNatural
from nlme.glsstruct import GlsStruct
from nlme.recalc import recalc
from nlme.var_power import initialize as vp_initialize
from nlme.var_power import varPower

DATA = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True, slots=True)
class FixtureDim:
    """``Dim`` of an initialized correlation object, read from the R fixtures."""

    N: int
    M: int
    max_len: int
    sum_len_sq: int
    len: tuple
    start: tuple

    def as_pdims(self) -> np.ndarray:
        parts = [self.N, self.M, self.max_len, self.sum_len_sq]
        parts.extend(self.len)
        parts.extend(self.start)
        return np.asarray(parts, dtype=np.int32)


def dim_from(d: dict) -> FixtureDim:
    return FixtureDim(
        N=int(d["N"]),
        M=int(d["M"]),
        max_len=int(d["maxLen"]),
        sum_len_sq=int(d["sumLenSq"]),
        len=tuple(d["len"]),
        start=tuple(d["start"]),
    )


oats = json.loads((DATA / "gls-oats-corAR1.json").read_text())
fx = json.loads((DATA / "recalc-fixtures.json").read_text())

# A. corAR1 on the Oats fit, same inputs as the glsEstimate proof.
n_a, p_a = int(oats["N"]), int(oats["p"])
xy_a = np.asarray(oats["xy"], dtype=np.float64).reshape((n_a, p_a + 1), order="F")
gls_a = GlsStruct(
    components={
        "corStruct": CorAR1(value=float(oats["cor_value"][0]), fixed=False, dim=dim_from(oats["dim"]))
    },
    pmap=np.asarray([[True]]),
    fixedSigma=False,
)
con_a = ConLin(
    Xy=xy_a,
    dims={"N": n_a, "p": p_a, "REML": int(oats["REML"])},
    logLik=0.0,
    sigma=0.0,
    fixedSigma=False,
    names=tuple(oats["xy_names"]),
)

# B and C. Orthodont design in data order: distance ~ age + Sex, Sex levels Male, Female.
orth = pd.read_csv(DATA / "gls-orthodont.csv")
orth["Sex"] = pd.Categorical(orth["Sex"], categories=["Male", "Female"])
from formulaic import model_matrix

mm = model_matrix("distance ~ age + Sex", orth)
x_orth = np.asarray(mm.rhs, dtype=np.float64)
xy_orth = np.column_stack([x_orth, orth["distance"].to_numpy(dtype=np.float64)])
n_o, p_o = x_orth.shape
con_orth = ConLin(
    Xy=xy_orth,
    dims={"N": n_o, "p": p_o, "REML": 1},
    logLik=0.0,
    sigma=0.0,
    fixedSigma=False,
)

# corNatural: the unconstrained values, dims, and covariate are the R fixtures.
cn_dim = dim_from(fx["cn_dim"])
cn = CorNatural(
    value=np.asarray(fx["cn_value"], dtype=np.float64),
    formula="~ 1 | Subject",
    fixed=False,
    max_cov=int(fx["cn_maxCov"]),
    covariate=list(fx["cn_covariate"]),
    dim=cn_dim,
)
gls_cn = GlsStruct(components={"corStruct": cn}, fixedSigma=False)

vp = vp_initialize(varPower(0.35, form="~ age"), orth)
gls_vp = GlsStruct(components={"varStruct": vp}, fixedSigma=False)


def recal(gls_st, con):
    r = recalc(gls_st, con)
    return np.concatenate(
        [np.asarray(r.Xy, dtype=np.float64).reshape(-1, order="F"), np.array([float(r.logLik)])]
    )


def one():
    return np.concatenate(
        [recal(gls_a, con_a), recal(gls_cn, con_orth), recal(gls_vp, con_orth)]
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
