import math
import statistics
import time

import numpy as np

from survival.dsurvreg import _density_gaussian
from survival.survreg_dtest import survregDtest


def _serialize(x):
    if x is True:
        return "TRUE"
    if x is False:
        return "FALSE"
    return "|".join(x)


def _mycauchy():
    # R example uses init<- instead of init=, so init is not in the list.
    return {
        "name": "Cauchy",
        "density": lambda x, parms=None: _mycauchy_density(x),
        "quantile": lambda p, parms: np.tan((p - 0.5) * math.pi),
        "deviance": lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("deviance residuals not defined")),
    }


def _mycauchy_density(x):
    x = np.asarray(x, dtype=float)
    temp = 1.0 / (1.0 + x * x)
    return np.column_stack(
        (
            0.5 + np.arctan(temp) / math.pi,
            0.5 + np.arctan(-temp) / math.pi,
            temp / math.pi,
            -2.0 * x * temp,
            2.0 * temp * temp * (4.0 * x * x * temp - 1.0),
        )
    )


def _gaussian():
    return {
        "name": "Gaussian",
        "init": lambda x, weights, **kwargs: None,
        "deviance": lambda y, scale, parms: None,
        "density": lambda x, parms=None: _density_gaussian(x, parms),
        "quantile": lambda p, parms: None,
    }


def _weibull():
    return {
        "name": "Weibull",
        "dist": "extreme",
        "trans": lambda y: np.log(np.asarray(y, dtype=float)),
        "dtrans": lambda y: 1.0 / np.asarray(y, dtype=float),
        "itrans": lambda x: np.exp(np.asarray(x, dtype=float)),
    }


def one():
    myc = _mycauchy()
    return [
        _serialize(survregDtest(myc, verbose=True)),
        _serialize(survregDtest(myc, verbose=False)),
        _serialize(survregDtest(_gaussian())),
        _serialize(survregDtest(_weibull())),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
