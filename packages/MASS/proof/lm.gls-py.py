import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")

from mass.lm_gls import lm_gls

stackloss = {
    "Air.Flow": [80, 80, 75, 62, 62, 62, 62, 62, 58, 58, 58, 58, 58, 58, 50, 50, 50, 50, 50, 56, 70],
    "Water.Temp": [27, 27, 25, 24, 22, 23, 24, 24, 23, 18, 18, 17, 18, 19, 18, 18, 19, 19, 20, 20, 20],
    "Acid.Conc.": [89, 88, 90, 87, 87, 87, 93, 93, 87, 80, 89, 88, 82, 93, 89, 86, 72, 79, 80, 82, 91],
    "stack.loss": [42, 37, 37, 28, 18, 18, 19, 20, 15, 14, 14, 13, 11, 12, 8, 7, 8, 8, 9, 15, 15],
}


def one():
    n = len(stackloss["stack.loss"])
    rho = 0.3
    idx = np.arange(n)
    w = rho ** np.abs(idx[:, None] - idx[None, :])
    fit = lm_gls("stack.loss ~ .", data=stackloss, W=w)
    return np.concatenate(
        [
            np.asarray(fit.coefficients, dtype=float).reshape(-1),
            [fit.rank, fit.df_residual],
            np.asarray(fit.residuals, dtype=float).reshape(-1),
            np.asarray(fit.fitted_values, dtype=float).reshape(-1),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % float(np.median(elapsed)))
