import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nlme.conlin import ConLin
from nlme.corar1 import CorAR1
from nlme.gls import GlsObject
from nlme.glsapvar import glsApVar
from nlme.glsstruct import GlsStruct
from nlme.intervals import intervals

FIXTURE = Path(__file__).resolve().parent / "data" / "gls-oats-corAR1.json"


@dataclass(frozen=True, slots=True)
class FixtureDim:
    """``Dim`` of an initialized corAR1 object, read from the R fixture."""

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


def load_fit():
    """The Oats gls fit with corAR1(form = ~ 1 | Block), as R fitted it."""
    fx = json.loads(FIXTURE.read_text())
    n, p = int(fx["N"]), int(fx["p"])
    xy = np.asarray(fx["xy"], dtype=np.float64).reshape((n, p + 1), order="F")
    d = fx["dim"]
    dim = FixtureDim(
        N=int(d["N"]),
        M=int(d["M"]),
        max_len=int(d["maxLen"]),
        sum_len_sq=int(d["sumLenSq"]),
        len=tuple(d["len"]),
        start=tuple(d["start"]),
    )
    cor = CorAR1(value=float(fx["cor_value"][0]), fixed=False, dim=dim)
    gls_st = GlsStruct(components={"corStruct": cor}, pmap=np.asarray([[True]]), fixedSigma=False)
    dims = {"N": n, "p": p, "REML": int(fx["REML"])}
    con = ConLin(
        Xy=xy,
        dims=dims,
        logLik=0.0,
        sigma=0.0,
        fixedSigma=False,
        names=tuple(fx["xy_names"]),
    )
    fit = fx["fit"]
    k = len(fit["coefficients"])
    # The apVar matrix is the translated glsApVar, computed in the untimed setup.
    apvar = glsApVar(gls_st, float(fx["sigma"]), con)
    obj = GlsObject(
        modelStruct=gls_st,
        dims=dims,
        coefficients=np.asarray(fit["coefficients"], dtype=np.float64),
        coef_names=tuple(fit["coef_names"]),
        varBeta=np.asarray(fit["varBeta"], dtype=np.float64).reshape((k, k), order="F"),
        sigma=float(fx["sigma"]),
        apVar=apvar,
        logLik=float(fit["logLik"]),
        numIter=0,
        fitted=np.zeros(0, dtype=np.float64),
        residuals=np.zeros(0, dtype=np.float64),
        method="REML",
        fixedSigma=False,
    )
    return obj


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
