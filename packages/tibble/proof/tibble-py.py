import statistics
import time

from tibble import tibble
def one():
    return ",".join(str(v) for v in tibble(a=[1, 2, 3], b=1)["b"])

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
