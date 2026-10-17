import statistics
import time
import warnings

import numpy as np

from survival.agexact_fit import agexact_fit
from survival.control import coxph_control


start = np.array([0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0], dtype=float)
stop = np.array([3, 3, 3, 4, 5, 5, 6, 1, 2, 2, 4, 4, 4, 6], dtype=float)
event = np.array([1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0], dtype=float)
x1 = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1], dtype=float)
x2 = np.array([1.2, -0.4, 0.5, 2.0, -1.1, 0.8, 0.3, -0.7, 1.5, 0.2, -1.4, 0.6, 1.1, -0.2], dtype=float)
strata = np.array([1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2], dtype=float)
offset = np.array([0, 0.1, 0, -0.2, 0.05, 0, 0, 0, -0.15, 0.2, 0, 0.05, 0, -0.1], dtype=float)
init = np.array([0.2, -0.3], dtype=float)

time2 = np.array([5, 4, 8, 2, 9, 6, 3, 7], dtype=float)
status2 = np.array([1, 1, 0, 1, 1, 0, 1, 1], dtype=float)
x2a = np.array([1.2, 0.4, 2.1, -0.3, 0.8, 1.5, -1.2, 0.1], dtype=float)
x2b = np.array([0, 1, 0, 1, 1, 0, 1, 0], dtype=float)

control = coxph_control(eps=1e-9, toler_chol=1e-12, iter_max=20)


def flat(fit):
    vals = np.concatenate(
        [
            np.asarray(fit["coefficients"], dtype=float).reshape(-1),
            np.ravel(np.asarray(fit["var"], dtype=float), order="F"),
            np.asarray(fit["loglik"], dtype=float).reshape(-1),
            np.array([fit["score"]], dtype=float),
            np.array([fit["iter"]], dtype=float),
            np.asarray(fit["means"], dtype=float).reshape(-1),
            np.asarray(fit["residuals"], dtype=float).reshape(-1),
            np.asarray(fit["linear.predictors"], dtype=float).reshape(-1),
        ]
    )
    return ["NA" if v != v else f"{v:.17g}" for v in vals]


def one():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit1 = agexact_fit(
            np.column_stack([x1, x2]),
            np.column_stack([start, stop, event]),
            strata,
            offset,
            init,
            control,
            None,
            "exact",
            None,
            True,
            (0, 1),
        )
        fit2 = agexact_fit(
            np.column_stack([x2a, x2b]),
            np.column_stack([time2, status2]),
            None,
            None,
            None,
            control,
            None,
            "exact",
            None,
            True,
            None,
        )
    return flat(fit1) + flat(fit2)


if __name__ == "__main__":
    value = one()
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000)
    print("\n".join(value))
    print("MS")
    print(f"{statistics.median(elapsed):.17g}")
