import statistics
import time

import numpy as np

from mass.addterm import _model_matrix, _qr_coef
from mass.studres import studres


stackloss = {
    "Air.Flow": [80, 80, 75, 62, 62, 62, 62, 62, 58, 58, 58, 58, 58, 58, 50, 50, 50, 50, 50, 56, 70],
    "Water.Temp": [27, 27, 25, 24, 22, 23, 24, 24, 23, 18, 18, 17, 18, 19, 18, 18, 19, 19, 20, 20, 20],
    "Acid.Conc.": [89, 88, 90, 87, 87, 87, 93, 93, 87, 80, 89, 88, 82, 93, 89, 86, 72, 79, 80, 82, 91],
    "stack.loss": [42, 37, 37, 28, 18, 18, 19, 20, 15, 14, 14, 13, 11, 12, 8, 7, 8, 8, 9, 15, 15],
}


class _LmFit:
    pass


def _lm(formula: str, data: dict) -> _LmFit:
    x, y, _names, _labels = _model_matrix(data, formula)
    coef, rank = _qr_coef(x, y)
    fit = _LmFit()
    fit.residuals = y - x @ coef
    fit.rank = rank
    fit.df_residual = int(y.shape[0] - rank)
    fit.weights = None
    fit.x = x
    fit.na_action = None
    return fit


def one():
    fit = _lm("stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", stackloss)
    return np.asarray(studres(fit), dtype=float).reshape(-1)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
