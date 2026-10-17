import statistics
import time

from survival.cipoisson import cipoisson


def one():
    a = cipoisson(4)
    b = cipoisson([0, 4, 10], time=[1, 2, 3])
    c = cipoisson(4, method="anscombe")
    d = cipoisson(4, time=0)
    return [
        f"{a[0]:.17g}",
        f"{a[1]:.17g}",
        f"{b[0, 0]:.17g}",
        f"{b[0, 1]:.17g}",
        f"{b[1, 0]:.17g}",
        f"{b[1, 1]:.17g}",
        f"{b[2, 0]:.17g}",
        f"{b[2, 1]:.17g}",
        f"{c[0]:.17g}",
        f"{c[1]:.17g}",
        "NA" if d[0] != d[0] else f"{d[0]:.17g}",
        "NA" if d[1] != d[1] else f"{d[1]:.17g}",
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
