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
from nlme.glsestimate import glsEstimate
from nlme.glsstruct import GlsStruct

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


def load_inputs():
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
    con = ConLin(
        Xy=xy,
        dims={"N": n, "p": p, "REML": int(fx["REML"])},
        logLik=0.0,
        sigma=0.0,
        fixedSigma=False,
        names=tuple(fx["xy_names"]),
    )
    return gls_st, con


def one(gls_st, con):
    fit = glsEstimate(gls_st, con)
    return np.concatenate(
        [
            np.asarray(fit.beta, dtype=np.float64).reshape(-1),
            np.array([fit.sigma, fit.logLik], dtype=np.float64),
            np.asarray(fit.varBeta, dtype=np.float64).reshape(-1, order="F"),
            np.asarray(fit.fitted, dtype=np.float64).reshape(-1),
            np.asarray(fit.resid, dtype=np.float64).reshape(-1),
        ]
    )


gls_st, con = load_inputs()
value = one(gls_st, con)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(gls_st, con)
    elapsed.append((time.perf_counter() - started) * 1000)
median = statistics.median(elapsed)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(v) for v in value), median)
)
