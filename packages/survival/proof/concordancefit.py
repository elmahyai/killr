import statistics
import time

from survival import Surv
from survival.concordancefit import concordancefit


def one():
    tempy = Surv([1, 2, 2, 2, 3, 4, 4, 4, 5, 2], [1, 0, 1, 0, 1, 0, 1, 1, 0, 1])
    tempx = [5, 5, 4, 4, 3, 3, 7, 6, 5, 4]
    fit2 = concordancefit(tempy, tempx, strata=None, weights=None)
    count = fit2["count"]
    if isinstance(count, dict):
        count = list(count.values())
    return [
        f"{fit2['concordance']:.17g}",
        *[f"{value:.17g}" for value in count],
        f"{fit2['var']:.17g}",
        f"{fit2['cvar']:.17g}",
        f"{fit2['n']}",
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
