import statistics
import time

from survival.cluster import cluster


def one():
    n = cluster([1, 1, 2, 2, 3, 3])
    ch = cluster(["a", "a", "b", "b"])
    f = cluster(["x", "y", "x"])
    return [*[f"{v:.17g}" for v in n], *ch, *f]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(str(v) for v in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
