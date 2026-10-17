import statistics
import time

from survival import Surv
from survival.surv_concordance import survConcordance


def one():
    tdata = {
        "time": [1, 2, 2, 2, 3, 4, 4, 4, 5, 2],
        "status": [1, 0, 1, 0, 1, 0, 1, 1, 0, 1],
        "x": [5, 5, 4, 4, 3, 3, 7, 6, 5, 4],
    }
    fit = survConcordance("Surv(time, status) ~ x", data=tdata)
    stats = fit["stats"]
    if stats.ndim > 1:
        stats = stats.reshape(-1)
    return [
        f"{fit['concordance']:.17g}",
        f"{fit['std.err']:.17g}",
        f"{fit['n']}",
        *[f"{value:.17g}" for value in stats],
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
