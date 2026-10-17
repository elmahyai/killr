import statistics
import time

from survival.aareg import aareg


def _serialize(fit):
    c = fit.coefficient
    tv = fit.test_var
    return [
        *[f"{v:.17g}" for v in fit.times],
        *[f"{v:.17g}" for v in fit.nrisk],
        *[f"{v:.17g}" for v in c.reshape(-1, order="F")],
        *[f"{v:.17g}" for v in fit.tweight.reshape(-1, order="F")],
        *[f"{v:.17g}" for v in fit.test_statistic],
        *[f"{v:.17g}" for v in tv.reshape(-1, order="F")],
    ]


def one():
    test1 = {
        "time": [4, 3, 1, 1, 2, 2, 3],
        "status": [1, None, 1, 0, 1, 1, 0],
        "x": [0, 2, 1, 1, 1, 0, 0],
    }

    fit = aareg("Surv(time, status) ~ x", test1)
    return _serialize(fit)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
