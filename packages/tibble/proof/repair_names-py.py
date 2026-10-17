import statistics
import time

from tibble import new_tibble, repair_names
frame = new_tibble([[1], [2]], names=["a", "a"], nrow=1)
def one():
    return ",".join(repair_names(frame).names)

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
