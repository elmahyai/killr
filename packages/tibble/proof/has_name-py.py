import statistics
import time

from tibble import has_name, new_tibble
frame = new_tibble([[1]], names=["a"], nrow=1)
def one():
    return f"{has_name(frame, 'a')},{has_name(frame, 'nope')}"

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
